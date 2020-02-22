import machine
import network
from ujson import dumps, load
from umqtt.simple import MQTTClient
from sensors.espsensors import ESPSensors

def wlan_connect(wifi_ssid, wifi_passwd, net_ip, net_mask, net_gw, net_dns):
    wdt = machine.WDT()
    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)
        wlan.ifconfig((net_ip, net_mask, net_gw, net_dns))
    if not wlan.isconnected():
        wlan.connect(wifi_ssid, wifi_passwd)
        t = 0
        while not wlan.isconnected() and t <= 3000:
            wdt.feed()
            machine.idle()
            t += 1
    return wlan

def do_deepsleep(time_in_seconds):
    network.WLAN(network.STA_IF).active(False)
    rtc = machine.RTC()
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    rtc.alarm(rtc.ALARM0, time_in_seconds * 1000)
    print('Going to deep sleep for {} seconds...'.format(time_in_seconds))
    print('I will be back!')
    machine.deepsleep()

def load_json_config(json_file = 'config.json'):
    with open(json_file, 'r') as f:
        json_config = load(f)
    f.close()
    return json_config

def main():
    print('Device UP!')
    wdt = machine.WDT()
    wdt.feed()

    sensor = ESPSensors(pin = config['dht_pin'], sensor_type = ['t','h'], sensor_model = config['dht_model'])
    sensor.set_name(config['device_name'])
    sensor.set_expire_after_seconds(int(config['sleep_time_sec']) + 10)
    sensor.register_sensor()
    wdt.feed()

    wlan = wlan_connect(config['wifi_ssid'], config['wifi_passwd'], config['net_ip'], config['net_mask'], config['net_gw'], config['net_dns'])
    print(wlan.ifconfig())
    wdt.feed()

    templates = sensor.get_template()
    discover_topics = sensor.get_discover_topic()
    values = sensor.get_value()
    print(values)
    json_attributes = {'name': config['device_name'], 'ip_address': wlan.ifconfig()[0]}
    mqtt_client = MQTTClient(config['device_name'],
        server = config['mqtt_server'],
        port = 1883,
        user = bytearray(config['mqtt_user'], 'utf-8'),
        password = bytearray(config['mqtt_password'], 'utf-8'))
    mqtt_client.connect()
    for s_type in ['temperature', 'humidity']:
        lwt_topic = templates[s_type]['availability_topic']
        mqtt_client.set_last_will(lwt_topic, 'offline', retain=True)
        wdt.feed()
        mqtt_client.publish(bytearray(lwt_topic), bytearray('online'), retain=True)
        wdt.feed()
        mqtt_client.publish(bytearray(discover_topics[s_type]), bytearray(dumps(templates[s_type])), retain=True, qos=0)
        wdt.feed()
        mqtt_client.publish(bytearray(templates[s_type]['state_topic']), bytearray(str(values[s_type])), retain=True, qos=0)
        wdt.feed()
        mqtt_client.publish(bytearray(templates[s_type]['json_attributes_topic']), bytearray(dumps(json_attributes)), retain=True, qos=0)
        wdt.feed()
    mqtt_client.disconnect()

if __name__ == '__main__':
    gc.collect()
    # Load configuration file
    config = load_json_config('config.json')
    main()
    do_deepsleep(config['sleep_time_sec'])
