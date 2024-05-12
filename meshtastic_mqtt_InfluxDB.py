# Persistent mqtt client, watch for voltage, telemetry, message packets and publish them to InfluxDB

import msh_influxDB_cloud
from datetime import datetime
import paho.mqtt.client as mqtt
import os
import sys
import json
import time
import pytz
import configparser

config = configparser.ConfigParser()
# Read the configuration file
config.read('config.ini')

if config.getboolean('GENERAL','PRINT_CONFIG'):
    # Iterate through sections and options to print all config values
    for section in config.sections():
        print(f"[{section}]")
        for key, value in config.items(section):
            print(f"{key} = {value}")
        print()  # Add an empty line between sections for better readability

PRINT_ALL_INCOMING = config['LOG']['PRINT_ALL_INCOMING']

# set your timezone here
TIMEZONE = config['GENERAL']['TIMEZONE']
CHANNEL_LIST = config['GENERAL']['CHANNEL_LIST']
MQTT_SERVER = config['MQTT']['SERVER']
MQTT_PORT = int(config['MQTT']['PORT'])
MQTT_USERNAME = config['MQTT']['USERNAME']
MQTT_PASSWORD = config['MQTT']['PASSWORD']
LOG_SNR = config.getboolean('LOG','SNR')
LOG_VOLTAGE = config.getboolean('LOG','VOLTAGE')
LOG_RSSI = config.getboolean('LOG','RSSI')
LOG_MESSAGE = config.getboolean('LOG','MESSAGE')
LOG_POSITION = config.getboolean('LOG','POSITION')
LOG_TRACEROUTE = config.getboolean('LOG','TRACEROUTE')
LOG_HOP_LIMIT = config.getboolean('LOG','HOP_LIMIT')
LOG_HOPS_AWAY = config.getboolean('LOG','HOPS_AWAY')
LOG_TYPE = config.getboolean('LOG','TYPE')
LOG_CHUTIL = config.getboolean('LOG','CHUTIL')
###### END SETTINGS ######

my_timezone = pytz.timezone('UTC')
channel_array = CHANNEL_LIST.split(',')
print("\n")
# mqttClient = mqtt.Client("mesh_aio_logger")
mqttClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="", clean_session=True, userdata=None)
mqttClient.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

node_db_filename = 'node_db.json'
global inlfux_string
inlfux_string = ""
#publish to InfluxDB
def publish_influx(inlfux_string):
        try:
            msh_influxDB_cloud.write(inlfux_string)
        except Exception as e:
            print(f"Error sending to InfluxDB:\n{inlfux_string} \n{str(e)}")
            pass
# read node_db file
def read_nodedb():
    global node_db_filename
    # Dict that will contain keys and values
    dictionary = {}
    with open(node_db_filename, "r") as json_file:
        node_db = json.load(json_file) 
        return node_db

# node_db stored in file , new nodes added to this files as the come, the file will be read at the start of the script
def write_nodedb(node, name_short, name_long):
    node_db[node] = [name_short, name_long]
    # with open(node_db_filename, 'r') as json_file:
    #     node_db_temp = json.load(json_file)
    # new_node = {node: [name_short, name_long]}
    # node_db_temp.update(new_node)
    with open(node_db_filename, 'w') as json_file:
        json.dump(node_db, json_file)

def write_log(string):
    with open("meshtastic_mgtt.log", 'a') as log:
        log.write(f"{time.asctime()} {string}\n")
    log.close        

node_db = read_nodedb()
print(node_db)


# def publish_packet(data):

#     feed = aio.feeds(AIO_FEED_GROUP+".messages")
#     if (data['from'] in node_db):
#         data['fname'] = node_db[data['from']]
#     if (data['to'] in node_db):
#         data['tname'] = node_db[data['to']]
#     # trim down the data. we really only want to see the message content
#     if 'stamp' in data:
#         stamp = datetime.fromtimestamp(data['timestamp'],my_timezone).strftime('%Y-%m-%d %H:%M:%S')
#     else:
#         current_time = datetime.now()  # Assuming UTC time
#         # Convert to the desired timezone (e.g., 'America/Los_Angeles' or your preferred timezone)
#         current_time = current_time.astimezone(my_timezone)
#         stamp = current_time.strftime('%Y-%m-%d %H:%M:%S')

#     trimmed = { 
#         'from' : data.get('fname',None) or data.get('from'),
#         'to'    : data.get('tname',None) or data.get('to'),
#         'channel' : data['channel'],
#         'message' : data['payload'],
#         'stamp' : stamp,
#         }
#     aio.send_data(feed.key, json.dumps(trimmed, indent=4))
#     print(trimmed)

def on_message(client, userdata, message):
    global inlfux_string
    try:
        data = json.loads(str(message.payload.decode("utf-8")))
        if PRINT_ALL_INCOMING:
            print("Got Packet")
            print(data)

    except Exception as e:
        print(e)
        return
    
    # check the topic of the message
    # if data['type'] == "text" and LOG_MESSAGE:
    #     # publish all message packets to the message log
    #     print(data)
    #     try:
    #         publish_packet(data)
    #     except Exception as e:
    #         print("error in publish:",e)

    # if data['type'] == "traceroute" and LOG_TRACEROUTE:
    #     print(data)
    #     try:
    #         publish_packet(data)
    #     except Exception as e:
    #         print("error in publish:",e)


    # "payload":{"altitude":113,"latitude_i":208759687,"longitude_i":-1565037665
    metadata = None        
    if data['type'] == 'position' and LOG_POSITION:
        metadata = {
            'lat': data['payload']['latitude_i'] / 10000000, #40.726190,
            'lon': data['payload']['longitude_i'] / 10000000, #-74.005334,
            'ele': data['payload'].get('altitude',None),
            'created_at': str(datetime.now(my_timezone)),
        }
    # update node_db if needed
    if data['type'] == 'nodeinfo':
        # add to the node_db if we haven't seen it before
        if str(data['from']) not in node_db:
            node = str(data['from'])
            name_short = data['payload']['shortname']
            name_long = data['payload']['longname']
            if "\\x00" in name_long or "\\u0000" in name_long or "\x00" in name_long:  # json don't like emojis
                pass
            name_long = name_long.replace('\x00','').replace('\\u0000','').replace('\\x00','').replace(' ','-').replace('.','-').replace('---','-').replace('--','-')
            write_nodedb(node, name_short, name_long)
            write_log(f"New Node found: {node}: {name_long} | {name_short} |")

    if str(data['from']) in node_db:
        node = str(data['from']) #will use node_db namesif we have them
        name_short = node_db.get(node)[0]
        name_long = node_db.get(node)[1]
        print(f"""Found Node in the node_db, will use {name_short} and {name_long} for {node}""")
    else: # otherwise we use node ID
        node = str(data['from'])
        name_short = 'ukn'
        name_long = 'ukn'
        print(f"**** Nodeinfo not found for {node}")
    try:
        if LOG_RSSI and 'rssi' in data and data['rssi'] != 0 and data['sender'] == '!da656a30':
            # publish_rssi(data)
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} rssi={data['rssi']}" # adding come after each measurement
            publish_influx(inlfux_string)
        if LOG_SNR and 'snr' in data and data['snr'] != 0 and data['sender'] == '!da656a30':
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} snr={data['snr']}" # adding come after each measurement
            publish_influx(inlfux_string)

        if LOG_VOLTAGE and 'payload' in data and 'voltage' in data['payload'] and data['payload'].get('voltage',0) != 0 and data['sender'] == '!da656a30':
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} batt={data['payload'].get('voltage',0)}" # 
            publish_influx(inlfux_string)

        if LOG_HOP_LIMIT and 'hop_limit' in data and data['sender'] == '!e2e18990' and data['from'] != 3664079408 and data['from'] != 3806431632:
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} hop_limit={data['hop_limit']}"
            publish_influx(inlfux_string)
            
        if LOG_HOPS_AWAY and 'hops_away' in data and data['sender'] == '!da656a30' and data['from'] != 3664079408 and data['from'] != 3806431632:
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} hops_away={data['hops_away']}" # 
            publish_influx(inlfux_string)

        if LOG_TYPE and 'type' in data and data['sender'] == '!da656a30' and data['from'] != 3664079408 and data['from'] != 3806431632:
            packet_type = str(data['type'])

            if 'payload' in data and 'route' in data['payload']: #this is Route response to Traceroute
                packet_type = 'route'
                write_log(f"Route: {data['payload']['route']}") 
                #write_log(f"Route: {data['payload']['route'].replace('[','| ').replace(']',' |').replace(',',' <>')}")   # will try to log the route response
            elif packet_type == "": # this is a Traceroute request
                packet_type = 'traceroute'
                to_node = str(data['to'])
                to_name_long = "Unknown"
                if to_node in node_db:
                    to_name_long = node_db.get(to_node)[1]
                else:
                    to_name_long = "Unknown"
                write_log(f"Traceroute from: {node} - {name_long} ===> {to_node} - {to_name_long}")  # will try to catch who sent it to who and store it in the local log file
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short},packet_type={packet_type} count=1"
            publish_influx(inlfux_string)

        if LOG_CHUTIL and data['type'] == 'telemetry' and data['sender'] == '!da656a30' and data['from'] != 3664079408 and data['from'] != 3806431632:
            inlfux_string = f"meshtastic,host={node},name_long={name_long},name_short={name_short} chan_util={data['payload'].get('channel_utilization',0)}"
            publish_influx(inlfux_string)
        inlfux_string = "" # reset inlfux string
        pass
    except Exception as e:
        print("Error sending to InfluxDB:", str(e))


mqttClient.on_message = on_message
#def on_log(client, userdata, level, buf):
    #print("log: ",buf)

#mqttClient.on_log=on_log

while(True):
    if (not mqttClient.is_connected()) :
        print("Connecting to mqtt server")
        mqttClient.connect(MQTT_SERVER, MQTT_PORT)
        mqttClient.loop_start()
        for channel in channel_array:
            print("Subscribing to msh/2/json/%s/#" % (channel))
            mqttClient.subscribe("msh/2/json/%s/#" % (channel))
            time.sleep(1)

    time.sleep(.01)

