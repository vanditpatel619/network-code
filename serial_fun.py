import serial
import re
from time import sleep
import json
from pprint import pprint
import sys
	
def main():
	console = Serial('COM3')
	console.send_command("\r\n")
	console.send_command("en")
	
	switches = get_switch_info(console)
	switch_data = import_switch_data('switches.json')
	config = Build_config()
	switch_config = config.return_config(switch_data, switches)
	configure_ssh(console, switch_data['hostname'], switch_data['domain'])

	
	
def import_switch_data(filename):
	with open(filename) as data_file:    
		data = json.load(data_file)
	return byteify(data)
	
def configure_ssh(console, hostname, domain):
	print "Configuring SSH..."
	console.enter_config()
	console.send_command('hostname ' + hostname)
	console.send_command('ip domain-name ' + domain)
	console.send_command_w_sleep('crypto key generate rsa modulus 1024', 7)
	console.send_command('ip ssh version 2')
	console.exit_config()
	print "Done!"


def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input		
	
def get_switch_info(console):
	out = console.send_command("show version")
	return parse_switch_info(out)

# Parse output of show version and return info of all the switches in the stack	
def parse_switch_info(show_ver):
	list = show_ver.split('\n')
	i = 0
	s_lines = []
	switches = []
	switches_parsed = []
	
	while i < len(list):
		if re.match('^.\s\s\s\s[0-9]', list[i]):
			s_lines.append(i)
		i = i+1	
	# Getting the lines with switch info	
	for l in s_lines:
		switches.append(list[l])
	# Parsing output and creating dictionary for each switch	
	for l in switches:
		a = l[1:].split()
		dict = {'num': a[0], 'port_count': a[1], 'model': a[2], 'ver': a[3], 'code': a[4]}
		switches_parsed.append(dict)
		
	return switches_parsed
	
def get_interface_list(console):
	out = console.send_command_f("show int status")
	return parse_interface_list(out)

# Probably not worth quering all the interfaces, though it may be useful for something.
def parse_interface_list(show_int_status):
	list = show_int_status.split('\n')
	int = []
	for line in list:
		if line.startswith('Gi') or line.startswith('Fa') or line.startswith('Te'):
			int.append(line.split()[0])
	return int	

#Not sure how useful this is, mostly for testing.	
def set_int_desc(console, list):
	enter_config(console)
	for line in list:
		console.send_command("int " + line)
		console.send_command("desc test for port " + line)
	exit_config(console)	
	
			
class Build_config: #class for building config based on templates

	def return_config(self, switch_data, switches):
		ip_int = self.return_ip_int(switch_data['ip_int'])
		vlans = self.return_vlans(switch_data['vlans'])
		int_config = self.return_int_config(switches, switch_data['vlans'], switch_data['voice'])
		routes = self.return_routes(switch_data['routes'])
		type = self.determine_switch_type(switches[0]['model'])
		main_config = self.return_main_config(type, switch_data['source_int'])
		config = {'ip_int' : ip_int, 'vlans' : vlans, 'int_config' : int_config, 'routes' : routes, 'main_config': main_config}
		return config
		
	def return_routes(self, routes):
		data = ''
		for l in routes:
			data = data + 'ip route ' + l + '\n'
		return data
	
	def return_vlans(self, vlans):
		data = ''
		for l in vlans:
			data = data + 'vlan ' + l['num'] + '\n name ' + l['name'] + '\n!\n'
		return data
		
	def return_ip_int(self, ip_int):
		data = ''
		for l in ip_int:
			data = data + "interface " + l['name'] + '\n description ' + l['desc'] + '\n ip address ' \
			+ l['ip'] + '\n no ip redirects\n!\n'
		return data
		
	def return_main_config(self, type, source_int):
		filename = type + '_template.txt'
		with open (filename, "r") as myfile:
			data=myfile.read()
		data = data.replace('*SOURCEVLAN*', source_int)
		return data	

	def return_int_config(self, switches, vlans, voice):
		i = 0
		data = ''
		for s in switches:
			d = self.create_int_config(s, vlans, voice)
			d = d.replace('*UserVlan*', 'vlan ' + vlans[0]['num'])
			d = d.replace('*VoiceVlan*', 'vlan ' + vlans[1]['num'])
			d = d.replace('*X*', str(i+1))
			d = d + '\n!\n'
			i = i+1
			data = data + d
		return data
	
	def create_int_config(self, switch, vlans, voice):
		range = self.determine_int_range(switch['model'])
		if voice:
			with open ("port_template_voice.txt", "r") as myfile:
				data=myfile.read()
		else:
			with open ("port_template.txt", "r") as myfile:
				data=myfile.read()
		int_config = 'int range ' + range + '\n' + data
		return int_config
	
	def determine_int_range(self, type):
		if '-48' in type:
			range = 'Gi*X*/0/1-48'
		elif '-8' in type:
			range = 'Fa*X*/0/1-8'
		elif '-12X48' in type:
			range = 'Gi*X*/0/1-36, Te*X*/0/37-48'
		else:
			range = 'unknown'
		return range
	
#Determine type of switches in the stack by looking at the 1st switch. Currently 2960 and 3850 are supported.	
	def determine_switch_type(self, type):
		line0 = re.search('-[A-Z]*\d*-', type)
		line1 = re.search('\d+', line0.group())
		if line1.group() == '2960':
			type = '2960'
		elif line1.group() == '3850':
			type = '3850'
		else:
			type = 'unknown'
		return type
	
	
	
class Serial:  #class for handling the serial console communications

	def __init__(self, com):
		self.serial_port = serial.Serial(com, baudrate=9600, timeout=None, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, xonxoff=False)
		self.serial_port.flushInput()
		print "connecting to port " + self.serial_port.name
		self.send_command("")
		self.send_command("terminal length 0")

	def enter_config(self):
		self.send_command("conf t")
			
	def exit_config(self):
		self.send_command("end")
		
	def send_command_f(self, str): #sending specificed command and returning cleaned up output (no command, no switch name)
		out = self.send_command(str)
		return self.filter_output(out)

	def send_command_w_sleep(self, str, slp): #sending specified command and returning the output, custom sleep when necessary
		self.serial_port.write(str.encode())
		self.serial_port.write("\r\n".encode())
		bytes_to_read = self.serial_port.inWaiting()
		sleep(slp)

		while bytes_to_read < self.serial_port.inWaiting():
			bytes_to_read = self.serial_port.inWaiting()
			sleep(slp)

		out = self.serial_port.read(bytes_to_read).decode()
		self.err_check(out)
		return out

	def err_check(self, out):
		list = out.split('\n')
		for l in list:
			if re.match('% Ambiguous', l) is not None or re.match('% Invalid', l) is not None:
				print "something went wrong, check the output:"
				print list[-1] + out
				sys.exit(1)
			elif re.match('% [A-Z]', l) is not None:
				print "there's some info, you may want to check it out: "
				print out
				return
		
	def send_command(self, str): #sending specified command and returning the output
		return self.send_command_w_sleep(str, .5)
		
	def filter_output(self, output):
		list = output.split('\n')
		return "\n".join(list[1:-2])
			
	def __del__(self):
		self.serial_port.close()
		print "closing serial port"
		
if __name__ == '__main__':
    main()