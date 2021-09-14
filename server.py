#!/usr/bin/env python3

import os
import socket
import threading
import binascii
import psycopg2
import psycopg2.extras
import time
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
            print(f"{datetime.now()}: IMEI registered. Car id: {car_id}")
        else:
            print(f"{datetime.now()}: IMEI not registered: {imei}")

    except (Exception, psycopg2.Error) as error:
        print(f"{datetime.now()}: Error while fetching data from PostgreSQL: {error}")

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
        print(f"{datetime.now()}: Store records to database")
        psycopg2.extras.execute_values(cursor, insert_query, record_data)

        connection.commit()

    except (Exception, psycopg2.Error) as error:
        print(f"{datetime.now()}: Error while fetching data from PostgreSQL: {error}")

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

    # parse packet
    codec = int(data[16:18], 16)

    # parse packet for teltonika codec 8 extended
    if (codec == 8):
        fields, response = codec8(data, car_id)
    elif (codec == 0x8E):
        fields, response = codec8e(data, car_id)
    else:
        print(f"{datetime.now()}: This codec is not implemented: {codec}")

    # store records to database
    if store_records(fields, car_id):
        # send records quantity to device
        return response


def handle_client(conn, car_id, stop):
    """ thread function communicating with device """

    try:
        message = '\x01'
        message = message.encode('utf-8')
        conn.send(message)

    except:
        print(f"{datetime.now()}: Error sending reply")

    else:
        while True:
            if stop():
                print(f"{datetime.now()}: Closing thread due to new connection for: {car_id}")
                # break
            try:
                data = conn.recv(2048)
                if data:
                    recieved = binascii.hexlify(data)
                    record = binascii.unhexlify(parse_packet(recieved, car_id))
                    conn.send(record)

            except socket.error:
                print(f"{datetime.now()}: Error Occured")
                break
            time.sleep(1)

    conn.close()


def start():
    """ main function """

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = os.environ.get('SERVER_HOST', '127.0.0.1')
    port = int(os.environ.get('SERVER_PORT', '12900'))
    s.bind((host, port))

    workers = {}
    s.listen()
    print(f"{datetime.now()}: Server is listening on {host}:{port}")

    while True:
        try:
            conn, addr = s.accept()
            print(f"{datetime.now()}: New connection {addr} connected")

        except:
            try:
                stop_threads = True
                for worker in workers.values():
                    worker.join()
                    print(f"{datetime.now()}: Killing thread {worker}")
                if conn:
                    conn.close()
                print(f"{datetime.now()}: Close connection due to exception")
            except: pass
            break

        # get IMEI
        imei = conn.recv(128)
        car_id = check_imei(str(imei)[10:-1])

        if car_id:
            if imei in workers.keys():
                # stop old thread
                stop_threads = True
                workers[imei].join()
                print(f"{datetime.now()}: Killing old thread {workers[imei]}")

            # create new thread
            stop_threads = False
            thread = threading.Thread(target=handle_client, args=(conn, car_id, lambda: stop_threads))
            workers[imei] = thread
            thread.start()
            print(f"{datetime.now()}: Start new thread: {workers[imei]}")
            print(f"{datetime.now()}: Active connections: {threading.activeCount() - 1} - {workers}")

        time.sleep(1)


print(f"{datetime.now()}: Server is starting...")
start()
