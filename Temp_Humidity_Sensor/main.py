import gc
import dht
import ujson
import utime
import machine
import network
from umqtt.simple import MQTTClient

def do_deepsleep(time_in_seconds):
    if time_in_seconds > 0:
        rtc = machine.RTC()
        rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
        rtc.alarm(rtc.ALARM0, time_in_seconds * 1000)
        print('Going to deep sleep for {} seconds...'.format(time_in_seconds))
        print('I will be back!')
        machine.deepsleep()
    else:
        print('Fake sleep')
        utime.sleep(time_in_seconds * -1)

def wlan_connect(essid = '', password = '', timeout = 30):
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
    if not wlan.isconnected():
        print('Scanning network...')
        scan_result = wlan.scan()
        print('Done!')
        ap_in_range = False
        for ap in scan_result:
            if bytearray(essid, 'utf-8') == ap[0]:
                ap_in_range = True
                break
        if ap_in_range:
            print('AP "{}" is in range! Trying to connect...'.format(essid))
            wlan.connect(str(essid), str(password))
            timeout_counter = 0
            while not wlan.isconnected() and timeout_counter < timeout:
                utime.sleep(1)
                timeout_counter += 1
            if timeout_counter >= timeout:
                print('Connection attempts timed out')
        else:
            print('AP "{}" not in range.'.format(essid))
    if wlan.isconnected():
        return True
    wlan.active(False)
    return False

def load_json_config(json_file = 'config.json'):
    with open(json_file, 'r') as f:
        json_config = ujson.load(f)
    f.close()
    return json_config

def send_autodiscover():
    for s in sensors:
        print('Sending autodiscover to {}'.format(s))
        mqtt_client.publish(
            topic = bytearray(sensors[s]['config_topic']),
            msg = bytearray(ujson.dumps(sensors[s]['config']), 'utf-8')
        )
    # Wait for HA to settle
    utime.sleep(5)
    return True

def send_online():
    for s in sensors:
        mqtt_client.publish(
            topic = bytearray(sensors[s]['config']['availability_topic']),
            msg = bytearray('online', 'utf-8')
        )
    utime.sleep(5)
    return True

def lwt_call_back(topic, msg):
    send_autodiscover()

def compare_value_in_range(v_current, v_target, r):
    if ( float(v_current) >= float(v_target) - float(r) ) and ( float(v_current) <= float(v_target) + float(r) ):
        return True
    return False
def convert_ms_to_human(sec):
    days = int(sec // 86400)
    hours = int(sec // 3600 % 24)
    minutes = int(sec // 60 % 60)
    seconds = int(sec % 60)
    return '{:d} days, {:02d}:{:02d}:{:02d}'.format(days,hours,minutes,seconds)

if __name__ == '__main__':
    print('Device UP!')
    gc.collect()
    machine.RTC().datetime()
    now = utime.mktime(utime.localtime())

    # Load configuration files
    config = load_json_config('config.json')
    sensors = ujson.loads(ujson.dumps(load_json_config('sensors.json')).replace('{DEVICENAME}',config['device_name']))

    mqtt_client = MQTTClient(config['device_name'],
        server = config['mqtt_server'],
        port = 1883,
        user = bytearray(config['mqtt_user'], 'utf-8'),
        password = bytearray(config['mqtt_password'], 'utf-8'))

    if config['dht_model'] == "11":
        dht_sensor = dht.DHT11(machine.Pin(int(config['dht_pin'])))
    elif config['dht_model'] == "22":
        dht_sensor = dht.DHT22(machine.Pin(int(config['dht_pin'])))
    else:
        raise Exception('DHT Sensor not defined')
    dht_sensor.measure()

    try:
        with open('data.json', 'r') as data_file:
            last_measurements = ujson.load(data_file)
        data_file.close()
    except OSError:
        last_measurements = {'t': 0, 'h': 0, 'd': 0}

    need_to_report = False
    if not compare_value_in_range(last_measurements['t'], dht_sensor.temperature(), config['temp_threshold']):
        print('Temperature threshold')
        need_to_report = True
    if not compare_value_in_range(last_measurements['h'], dht_sensor.humidity(), config['hum_threshold']):
        print('Humidity threshold')
        need_to_report = True
    if int(now) - int(last_measurements['d']) >= int(config['time_threshold']):
        print('Time threshold')
        need_to_report = True
    if machine.reset_cause() != machine.DEEPSLEEP_RESET:
        print('First boot')
        need_to_report = True
    if not need_to_report:
        print('Last report sent {} seconds ago'.format(int(now) - int(last_measurements['d'])))
        print('Nothing changed since last measurement...')
    else:
        # Connect to Wi-Fi
        while not wlan_connect(
                    essid = config['wifi_ssid'],
                    password = config['wifi_passwd'],
                    timeout = int(config['wifi_timeout_sec'])):
            print('Wi-Fi connection timed out.')
            do_deepsleep(30)
        # Device is connect at this point.
        print('My IP Address: {}'.format(network.WLAN(network.STA_IF).ifconfig()[0]))
        print('Connecting to MQTT...')
        mqtt_client.connect()
        utime.sleep(1)
        send_autodiscover()
        send_online()
        print('Temperature: {}'.format(dht_sensor.temperature()))
        mqtt_client.publish(
            topic = bytearray(sensors['temperature']['config']['state_topic']),
            msg = bytearray(str(dht_sensor.temperature()), 'utf-8')
        )
        utime.sleep(1)
        print('Humidity: {}'.format(dht_sensor.humidity()))
        mqtt_client.publish(
            topic = bytearray(sensors['humidity']['config']['state_topic']),
            msg = bytearray(str(dht_sensor.humidity()), 'utf-8')
        )
        utime.sleep(1)
        mqtt_client.publish(
            topic = bytearray(sensors['temperature']['config']['json_attributes_topic']),
            msg = bytearray(ujson.dumps({'uptime': convert_ms_to_human(now),'ip_address': network.WLAN(network.STA_IF).ifconfig()[0]}), 'utf-8')
        )
        utime.sleep(1)
        mqtt_client.disconnect()
        last_measurements = {'t':dht_sensor.temperature(),'h':dht_sensor.humidity(),'d':now}
        with open('data.json', 'w') as data_file:
            ujson.dump(last_measurements, data_file)
        data_file.close()
        utime.sleep(5)
    do_deepsleep(int(config['sleep_time_sec']))
