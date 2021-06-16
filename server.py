#!/usr/bin/env python3

import socket
import threading
import binascii
import psycopg2
import psycopg2.extras
from datetime import datetime
import uuid
import json

from config import config

HOST = '127.0.0.1'
PORT = 12900

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))


def check_imei(imei):
    """ Check if car with such imei is registered in database and return car id if exists"""

    car_id = None

    try:
        params = config()
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()

        sql = f"SELECT id FROM car_car WHERE sim_imei = '{imei}';"
        cursor.execute(sql)
        car_id = cursor.fetchone()

        if car_id:
            print("IMEI registered. Car id:", car_id)
        else:
            print("IMEI not registered:", imei)

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()

    return car_id


def store_records(record_data):
    """ store records to database """

    try:
        params = config()
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()
        psycopg2.extras.register_uuid()

        insert_query = "INSERT INTO tracking_record (id, car_id, timestamp, priority, \
                                                     longitude, latitude, altitude, \
                                                     angle, satellites, speed, \
                                                     event_id, io_elements, \
                                                     created_at, updated_at) \
                                                     VALUES %s"
        print("Store records to database" + "\n")
        psycopg2.extras.execute_values(cursor, insert_query, record_data)

        connection.commit()

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()


def parse_packet(data, car_id):
    """ Parse packet data and store it to database"""

    # parse packet
    codec = int(data[16:18], 16)
    records = int(data[18:20], 16)
    response = '000000' + data[18:20].decode("utf-8")
    fields = []

    # parse packet for teltonika codec 8 extended
    if (codec == 0x8E):
        index = 20

        for _ in range(records):
            timestamp = datetime.fromtimestamp(int(data[index:index+16], 16)/1000)
            priority = int(data[index+16:index+18], 16)
            lon = int(data[index+18:index+26], 16)
            lat = int(data[index+26:index+34], 16)
            alt = int(data[index+34:index+38], 16)
            angle = int(data[index+38:index+42], 16)
            sats = int(data[index+42:index+44], 16)
            speed = int(data[index+44:index+48], 16)
            event_id = int(data[index+48:index+52], 16)
            created_at = datetime.now()
            updated_at = datetime.now()
            io_elements = {}
            index += 56

            # parse IO Elements
            for bytes in [1, 2, 4, 8, 16]:
                elements = int(data[index:index+4], 16)
                index += 4

                for _ in range(elements):
                    key = int(data[index:index+4], 16)
                    value = int(data[index+4:index+4+bytes*2], 16)
                    io_elements[key] = value
                    index += 4 + bytes*2

            fields.append((uuid.uuid4(), car_id, timestamp, priority, lon, lat, alt, angle, sats, speed,
                          event_id, json.dumps(io_elements), created_at, updated_at))
            print("Timestamp: " + str(timestamp) + "\nLat,Lon: " + str(lat) + ", " + str(lon) + "\nAltitude: " + str(alt) +
                  "\nSats: " +  str(sats) + "\nSpeed: " + str(speed) + "\nIO Elements" + str(io_elements))

    # store records to database
    store_records(fields)

    # send records quantity to device
    return response


def handle_client(conn, addr):
    """ thread function communicating with device """

    print(f"[NEW CONNECTION] {addr} connected.")
    imei = conn.recv(128)
    car_id = check_imei(str(imei)[10:-1])

    if car_id:
        try:
            message = '\x01'
            message = message.encode('utf-8')
            conn.send(message)

        except:
            print("Error sending reply. Maybe it's not our device")

        while True:

            try:
                data = conn.recv(2048)
                recieved = binascii.hexlify(data)
                record = binascii.unhexlify(parse_packet(recieved, car_id))
                conn.send(record)

            except socket.error:
                print("Error Occured.")
                break

    conn.close()


def start():
    """ main function """

    s.listen()
    print(" Server is listening ...")

    while True:
        conn, addr = s.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")

print("[STARTING] server is starting...")

start()
