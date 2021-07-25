#!/usr/bin/env python3

import os
import socket
import threading
import binascii
import psycopg2
import psycopg2.extras
from datetime import datetime

from teltonika import codec8, codec8e


db_params = psycopg2.extensions.make_dsn(host = os.environ['DB_HOST'],
                                         port = os.environ['DB_PORT'],
                                         dbname = os.environ['DB_NAME'],
                                         user = os.environ['DB_USER'],
                                         password = os.environ['DB_PASSWORD']
                                         )

def check_imei(imei):
    """ Check if car with such imei is registered in database and return car id if exists"""

    car_id = None
    connection = None

    try:
        connection = psycopg2.connect(db_params)
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


def store_records(record_data, car_id):
    """ store records to database """

    connection = None

    try:
        succeed = False
        connection = psycopg2.connect(db_params)
        cursor = connection.cursor()
        psycopg2.extras.register_uuid()

        insert_query = "INSERT INTO tracking_record (id, car_id, timestamp, priority, \
                                                     longitude, latitude, altitude, \
                                                     angle, satellites, speed, \
                                                     event_id, is_parked, io_elements, \
                                                     created_at, updated_at) \
                                                     VALUES %s"
        print("Store records to database" + "\n")
        psycopg2.extras.execute_values(cursor, insert_query, record_data)

        connection.commit()

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

    else:
        succeed = True

    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
        return succeed


def parse_packet(data, car_id):
    """ Parse packet data and store it to database"""

    print('Car ID:', car_id, ' Data:', data)
    # parse packet
    codec = int(data[16:18], 16)

    # parse packet for teltonika codec 8 extended
    if (codec == 8):
        fields, response = codec8(data, car_id)
    elif (codec == 0x8E):
        fields, response = codec8e(data, car_id)
    else:
        print('This codec is not implemented:', codec)

    # store records to database
    if store_records(fields, car_id):
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
                if data:
                    recieved = binascii.hexlify(data)
                    record = binascii.unhexlify(parse_packet(recieved, car_id))
                    conn.send(record)

            except socket.error:
                print("Error Occured.")
                break

    conn.close()


def start():
    """ main function """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = os.environ.get('SERVER_HOST', '127.0.0.1')
    port = int(os.environ.get('SERVER_PORT', '12900'))

    s.bind((host, port))

    s.listen()
    print(f"Server is listening on {host}:{port}")

    while True:
        try:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}")
        except KeyboardInterrupt:
            try:
                if conn:
                    conn.close()
            except: pass
            break

print("[STARTING] server is starting...")

start()
