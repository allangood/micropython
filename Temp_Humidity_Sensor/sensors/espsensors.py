import dht
from ds18x20 import DS18X20
from onewire import OneWire
from ubinascii import hexlify
from machine import unique_id, Pin

class ESPSensors:
  def __init__(self, pin = 99, sensor_type = 't', sensor_model = 'DHT22'):
      self.id = hexlify(unique_id()).decode('utf-8')
      self.name = self.id
      self.pin = int(pin)
      self.sensor_handle = None
      self.sensor_type = sensor_type
      self.sensor_model = sensor_model
      self.set_sensor_type(sensor_type)
      self.set_sensor_model(sensor_model)
      self.discovery_prefix = 'homeassistant'
      self.template = {}
      self.discover_topic = {}
      self.expire_after = '1800'
      self.state = 'N/A'

  def get_id(self):
      return self.id

  def set_pin(self, pin):
      self.pin = int(pin)

  def get_pin(self):
      return int(self.pin)

  def get_name(self):
      return self.name

  def set_name(self, name):
      self.name = name

  def set_expire_after_seconds(self, seconds):
      self.expire_after = str(seconds)

  def set_sensor_type(self, sensor_type):
      if any(x in sensor_type for x in ['temperature', 'temp', 't', 'humidity', 'hum', 'h', 'door', 'binary', 'bin']):
          self.sensor_type = sensor_type
      else:
          raise Exception('Type "{}" not supported.'.format(sensor_type))

  def add_sensor_type(self, sensor_type):
      if type(self.sensor_type) == type(''):
          # Type is a string, must be converted to a list
          self.sensor_type = [self.sensor_type, sensor_type]
      elif type(self.type) == type([]):
          # Type is a list, just add a new value
          self.sensor_type.append(sensor_type)

  def remove_sensor_type(self, sensor_type):
      if type(self.sensor_type) == type('') and self.sensor_type == sensor_type:
          # Type is a string, set type to an empty string
          self.sensor_type = ''
      elif type(self.sensor_type) == type([]):
          # Type is a list, remove the sensor_type
          self.sensor_type.remove(sensor_type)

  def get_sensor_type(self):
      return self.sensor_type

  def set_sensor_model(self, sensor_model):
      if sensor_model.upper() in ['DHT22', 'DHT11', 'DS18B20', 'SWITCH']:
          self.sensor_model = sensor_model.upper()
      else:
          raise Exception('Model "{}" not supported.'.format(sensor_model))

  def get_sensor_model(self):
      return self.sensor_model

  def register_sensor(self):
      if self.pin > 16 or self.pin < 0:
          raise Exception('Invalid GPIO {}'.format(self.pin))
      if self.sensor_model == "DHT11":
          self.sensor_handle = dht.DHT11(Pin(self.pin))
      elif self.sensor_model == "DHT22":
          self.sensor_handle = dht.DHT22(Pin(self.pin))
      elif self.sensor_model == 'DS18B20':
          self.sensor_handle = DS18X20(OneWire(self.pin))
          self.sensor_handle.convert_temp()
      elif self.sensor_model == 'SWITCH':
          self.sensor_handle = Pin(self.pin, Pin.IN, Pin.PULL_UP)
      return True

  def get_value(self):
      if self.sensor_model in ['DHT11', 'DHT22']:
          self.sensor_handle.measure()
          return {'temperature': self.sensor_handle.temperature(), 'humidity': self.sensor_handle.humidity()}
      elif self.sensor_model == 'DS18B20':
          roms = self.sensor_handle.scan()
          return round(self.sensor_handle.read_temp(roms[0]),2)
      elif self.sensor_model == 'SWITCH':
          return self.sensor_handle.value()
      else:
          raise Exception('DHT Sensor not defined')
      return 0

  def set_discovery_prefix(self, discovery_prefix):
      self.discovery_prefix = discovery_prefix

  def get_discover_topic(self):
      if any(x in self.sensor_type for x in ['temperature', 'temp', 't']):
          self.discover_topic['temperature'] = "{prefix}/sensor/{id}/{name}_temperature/config".format(prefix=self.discovery_prefix, id=self.id, name=self.name)
      if any(x in self.sensor_type for x in ['humidity', 'hum', 'h']):
          self.discover_topic['humidity'] = "{prefix}/sensor/{id}/{name}_humidity/config".format(prefix=self.discovery_prefix, id=self.id, name=self.name)
      return self.discover_topic

  def get_template(self):
      # https://www.home-assistant.io/docs/mqtt/discovery/
      if any(x in self.sensor_type for x in ['temperature', 'temp', 't']):
          self.template['temperature'] = {
            'name': '{}_temperature'.format(self.name),
            'unit_of_measurement': '°C',
            'device_class': 'temperature',
            'expire_after': self.expire_after,
            'device' : { 'identifiers': self.id,  'manufacturer': 'Espressif', 'model': 'NodeMCU-8266', 'name': self.name },
            'availability_topic': '{prefix}/sensor/{id}/{name}_temperature/availability'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
            'state_topic': '{prefix}/sensor/{id}/{name}_temperature/state'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
            'json_attributes_topic': '{prefix}/{id}/{name}_temperature/attributes'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
          }
      if any(x in self.sensor_type for x in ['humidity', 'hum', 'h']):
          self.template['humidity'] = {
            'name': '{}_humidity'.format(self.name),
            'unit_of_measurement': '%',
            'device_class': 'humidity',
            'expire_after': self.expire_after,
            'device' : { 'identifiers': self.id,  'manufacturer': 'Espressif', 'model': 'NodeMCU-8266', 'name': self.name },
            'availability_topic': '{prefix}/sensor/{id}/{name}_humidity/availability'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
            'state_topic': '{prefix}/sensor/{id}/{name}_humidity/state'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
            'json_attributes_topic': '{prefix}/{id}/{name}_humidity/attributes'.format(prefix=self.discovery_prefix, id=self.id, name=self.name),
          }
      if any(x in self.sensor_type for x in ['door', 'binary', 'bin']):
          self.template['binary'] = {}
          pass
      return self.template
