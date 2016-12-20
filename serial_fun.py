import serial
import re
from time import sleep
import company_internal #this is necessary to create proprietary config lines based on IP and VLAN schema

	
def main():
	console = Serial('COM3')
	console.send_command("\r\n")
	console.send_command("en")
	variables = {'varX': '1', 'varY': '3', 'loc': '3A'} #these values are needed for the pre-defined IP, VLAN and naming schema, not included in the script
	#int = get_interface_list(console)
	
	#set_int_desc(console, int)
	
	#print console.send_command_f("\n")
	
	switches = get_switch_info(console)
	conf = build_config(switches, variables)
	configure_ssh(console, conf['host'])
	

def configure_ssh(console, host):
	print "Configuring SSH..."
	enter_config(console)
	list = host.split('\n')
	for l in list:
		console.send_command(l)
	console.send_command_w_sleep('crypto key generate rsa 1024', 7)
	console.send_command('ip ssh version 2')
	exit_config(console)
	print "Done!"
	
def build_config(switches, variables):
	type = determine_switch_type(switches[0]['model'])
	# The following 2 calls return configuration lines for VLAN and Int VLAN interfaces, based on the pre-defined schema.
	# Due to proprietary nature of this info, these functions are not included.
	vlan_int =  company_internal.return_vlan_int(variables) 
	vlan, vlans = company_internal.return_vlan(variables) #vlans - list of vlans per switch, proprietary
	int_config = return_int_config(switches, vlans, False)
	default_route = company_internal.return_default_route(variables)
	hostname_domain = company_internal.return_hostname_domain(variables)
	main_config = return_main_config(type, vlans)
	config = {'vlan_int' : vlan_int, 'vlan' : vlan, 'int' : int_config, 'default' : default_route, 'host' : hostname_domain, 'main': main_config}
	return config
	
def return_main_config(type, vlans):
	filename = type + '_template.txt'
	with open (filename, "r") as myfile:
		data=myfile.read()
	data = data.replace('*SOURCEVLAN*', 'Vlan' + vlans[0]['num'])
	return data
	
	
# Following 3 functions will look at all the switches in the stack and will create configs for each switch in the stack
# files port_template_voice.txt and port_template.txt are necessary to function
# *UserVlan* and *VoiceVlan* are being replaced by the VLANs determined in the proprietary function
def return_int_config(switches, vlans, voice):
	i = 0
	data = ''
	for s in switches:
		d = create_int_config(s, vlans, voice)
		d = d.replace('*UserVlan*', vlans[0]['num'])
		d = d.replace('*VoiceVlan*', vlans[1]['num'])
		d = d.replace('*X*', str(i+1))
		d = d + '\n!\n'
		i = i+1
		data = data + d
	return data
	
def create_int_config(switch, vlans, voice):
	range = determine_int_range(switch['model'])
	if voice:
		with open ("port_template_voice.txt", "r") as myfile:
			data=myfile.read()
	else:
		with open ("port_template.txt", "r") as myfile:
			data=myfile.read()
	int_config = 'int range ' + range + '\n' + data
	return int_config
	
def determine_int_range(type):
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
def determine_switch_type(type):
	line0 = re.search('-[A-Z]*\d*-', type)
	line1 = re.search('\d+', line0.group())
	if line1.group() == '2960':
		type = '2960'
	elif line1.group() == '3850':
		type = '3850'
	else:
		type = 'unknown'
	return type

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
		if re.match('^.....[0-9]', list[i]):
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
	
			
def enter_config(console):
	console.send_command("conf t")
			
def exit_config(console):
	console.send_command("end")
			
class Serial:  #class for handling the serial console communications

	def __init__(self, com):
		self.serial_port = serial.Serial(com, baudrate=9600, timeout=None, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, xonxoff=False)
		self.serial_port.flushInput()
		print "connecting to port " + self.serial_port.name
		self.send_command("")
		self.send_command("terminal length 0")
	
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

		return self.serial_port.read(bytes_to_read).decode()
		
	def send_command(self, str): #sending specified command and returning the output
		return self.send_command_w_sleep(str, 1)
		
	def filter_output(self, output):
		list = output.split('\n')
		return "\n".join(list[1:-2])
			
	def __del__(self):
		self.serial_port.close()
		print "closing serial port"
		
if __name__ == '__main__':
    main()