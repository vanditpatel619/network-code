import serial
from time import sleep

	
def main():
	console = Serial('COM3')
	console.send_command("en")
	
	int = get_interface_list(console)
	
	set_int_desc(console, int)
	
	print console.send_command_f("show int desc")
	
def get_interface_list(console):
	out = console.send_command_f("show int status")
	list = out.split('\n')
	int = []
	for line in list:
		if line.startswith('Gi') or line.startswith('Fa'):
			int.append(line.split()[0])
	return int
			
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
			
class Serial:

	def __init__(self, com):
		self.serial_port = serial.Serial(com, baudrate=9600, timeout=None, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, xonxoff=False)
		self.serial_port.flushInput()
		print "connecting to port " + self.serial_port.name
		self.send_command("")
		self.send_command("terminal length 0")
	
	def send_command_f(self, str):
		out = self.send_command(str)
		return self.filter_output(out)
	
	def send_command(self, str):
		self.serial_port.write(str.encode())
		self.serial_port.write("\r\n".encode())
		bytes_to_read = self.serial_port.inWaiting()
		sleep(1)

		while bytes_to_read < self.serial_port.inWaiting():
			bytes_to_read = self.serial_port.inWaiting()
			sleep(1)

		return self.serial_port.read(bytes_to_read).decode()
		
	def filter_output(self, output):
		list = output.split('\n')
		return "\n".join(list[1:-2])
			
	def __del__(self):
		self.serial_port.close()
		print "closing serial port"
		
if __name__ == '__main__':
    main()