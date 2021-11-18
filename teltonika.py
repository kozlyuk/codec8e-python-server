from datetime import datetime
import uuid
import json


def codec8(data, car_id):
    """ Parse  packet for teltonika codec 8 extended """

    records = int(data[18:20], 16)
    response = '000000' + data[18:20].decode("utf-8")
    fields = []
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
        event_id = int(data[index+48:index+50], 16)
        is_parked = False
        created_at = datetime.now()
        updated_at = datetime.now()
        io_elements = {}
        index += 52

        # parse IO Elements
        for bytes in [1, 2, 4, 8]:
            elements = int(data[index:index+2], 16)
            index += 2

            for _ in range(elements):
                key = int(data[index:index+2], 16)
                value = int(data[index+2:index+2+bytes*2], 16)
                io_elements[key] = value
                index += 2 + bytes*2

        # set is_parked flag
        is_ignition_on = io_elements.get(239, 1)
        is_movement = io_elements.get(240, 1)
        if not is_ignition_on and not is_movement:
            is_parked = True

        # fix altitude tracker bug
        if alt > 32767:
            alt = 0

        fields.append((uuid.uuid4(), car_id, timestamp, priority, lon, lat, alt, angle, sats, speed,
                        event_id, is_parked, json.dumps(io_elements), created_at, updated_at))
        print("Timestamp: " + str(timestamp) + " Lat,Lon: " + str(lat) + ", " + str(lon) + " Altitude: " + str(alt) +
                " Sats: " +  str(sats) + " Speed: " + str(speed) + "\nIO Elements" + str(io_elements))

    return fields, response


def codec8e(data, car_id):
    """ Parse  packet for teltonika codec 8 """

    records = int(data[18:20], 16)
    response = '000000' + data[18:20].decode("utf-8")
    fields = []
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
        is_parked = False
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

        # set is_parked flag
        is_ignition_on = io_elements.get(239, 1)
        is_movement = io_elements.get(240, 1)
        if not is_ignition_on and not is_movement:
            is_parked = True

        fields.append((uuid.uuid4(), car_id, timestamp, priority, lon, lat, alt, angle, sats, speed,
                        event_id, is_parked, json.dumps(io_elements), created_at, updated_at))
        print("Timestamp: " + str(timestamp) + " Lat,Lon: " + str(lat) + ", " + str(lon) + " Altitude: " + str(alt) +
                " Sats: " +  str(sats) + " Speed: " + str(speed) + "\nIO Elements" + str(io_elements))

    return fields, response
