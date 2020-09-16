#! /usr/bin/python
import RPi.GPIO as GPIO
import time
import smbus
import math



#Servo MG996
#20ms (50Hz) period of PWM
#Positions: SEGUN DATAHSEET
#0 -  1.5ms pulse -- 90   NO SON LAS REALES, DA MENOS DE 90 Y 180 GRADOS
#1 -  2.0ms pulse -- 0
#2 -  1.0ms pulse -- 180
#|--------------------------------|#
#|-  20ms  =  100%               -|#
#|-    X   =  DC%                -|#
#|--------------------------------|#|--------------------------------|#
#|-    DC% =  (100*X)/ 20        -|#|-    X =  (DC*20)/ 100         -|#
#|-     X is in ms               -|#|-       X is in ms             -|#
#|--------------------------------|#|--------------------------------|#
#|1.5ms == 7.5   of DC            |#|   1.5ms  == 7.5                |#  90 GRADOS  
#|2.0ms == 10.0  of DC            |#|   2.5ms  == 12.5               |#   0 GRADOS
#|1.0ms ==  5.0  of DC            |#|   0.5ms  == 2.5                |# 180 GRADOS

#Positions: REALES
#-------ms-----DC-----GRADE
#0 -  1.5ms - 7.5  -- 90   
#1 -  2.5ms - 12.5 -- 0
#2 -  0.5ms - 2.5  -- 180

# 2.5 - 12.5 SON LOS 180 GRADOS
# 10/180 == 0.0555555
#INCREMENTO DE DC POR CADA GRADO == 0.055556 

servo_X_PIN = 17                #Puerto para el servo del eje x
servo_Y_PIN = 18                #Puerto para el servo del eje y
angle_increment = 0.05555556    #Cuanto vale cada angulo

#--------------------------------------------------------------------------------------#
# Inicializacion de los servos y sus pines
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_X_PIN, GPIO.OUT)
GPIO.setup(servo_Y_PIN, GPIO.OUT)

Servo_X = GPIO.PWM(servo_X_PIN, 50) # GPIO 17, Frecuencia de 50 Hz  T= 0.02seg= 1/50
Servo_Y = GPIO.PWM(servo_Y_PIN, 50) # GPIO 17, Frecuencia de 50 Hz  T= 0.02seg= 1/50

#Pone el servo a 90 grados
Servo_X.start(7.5)
Servo_Y.start(7.5)

#-------------------------------------------------------------------------------------------#
#   function name:       Servo_control                                                      #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#
def Servo_control(angle_x, angle_y):# Se tiene un rango de -90 a 90 (180 grados)
  
  if angle_x >= 0:
    _angle_X = 7.5 + angle_x*angle_increment  # si es giro a la izq
  elif angle_x < 0:
    _angle_X = 7.5 + angle_x*angle_increment  # si es giro a la der
  else:
    angle = 7.5  


  if angle_y >= 0:
    _angle_Y = 7.5 + angle_y*angle_increment  # si es giro a la izq
  elif angle_y < 0:
    _angle_Y = 7.5 + angle_y*angle_increment  # si es giro a la der
  else:
    angle = 7.5 
    
    
  Servo_X.ChangeDutyCycle(_angle_X)
  Servo_Y.ChangeDutyCycle(_angle_Y)
  time.sleep(0.05)

#-------------------------------------------------------------------------------------------#
#Giro Acelerometro MPU6050

#Power Managment registers
power_mqmt_1 = 0x6b
power_mqmt_2 = 0x6c

#Complemetary Filter Variables
dt = 0.001
#-------------------------------------------------------------------------------------------#
#   function name:       read_byte                                                          #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#
def read_byte(adr):
	return bus.read_byte_data(address, adr)


#-------------------------------------------------------------------------------------------#
#   function name:       read_word                                                          #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#
def read_word (adr):
	high = bus.read_byte_data(address, adr)
	low = bus.read_byte_data(address, adr+1)
	val = (high<<8) + low
	return val

#-------------------------------------------------------------------------------------------#
#   function name:       read_word_2c                                                       #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#
def read_word_2c(adr):
	val = read_word(adr)
	if(val >= 0x8000):
		return -((65535 - val)+1)
	else:
		return val

#-------------------------------------------------------------------------------------------#
#   function name:       dist                                                               #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#
def dist(a,b):

	return math.sqrt((a*a)+(b*b))
#-------------------------------------------------------------------------------------------#
#   function name:       get_y_rotation                                                     #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#  
def get_y_rotation(x,y,z):
	radians = math.atan2(x,dist(y,z))

	return math.degrees(radians)
#-------------------------------------------------------------------------------------------#
#   function name:       get_x_rotation                                                     #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#  
def get_x_rotation(x,y,z):
	radians = math.atan2(y, dist(x,z))
	return math.degrees(radians)  
  
#-------------------------------------------------------------------------------------------#
#   function name:       _rotation                                                          #
#   function description:                                                                   #
#-------------------------------------------------------------------------------------------#  
def _rotation():
    gyro_xout = read_word_2c(0x43)
    gyro_yout = read_word_2c(0x45)
    gyro_zout = read_word_2c(0x47)
    
    accel_xout = read_word_2c(0x3b)
    accel_yout = read_word_2c(0x3d)
    accel_zout = read_word_2c(0x3f)
    
    accel_xout_scaled = accel_xout / 16384.0
    accel_yout_scaled = accel_yout / 16384.0
    accel_zout_scaled = accel_zout / 16384.0
    
   
    RotacionX = get_x_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled)
    RotacionY = get_y_rotation(accel_xout_scaled, accel_yout_scaled, accel_zout_scaled) 
    
    angleX = 0.99*(RotacionX + (gyro_xout/131)*dt) + 0.1*accel_xout_scaled
    angleY = 0.99*(RotacionY + (gyro_yout/131)*dt) + 0.1*accel_yout_scaled
    
    #SE HACE EL CONTROL DE LOS SERVOS
    Servo_control(angleX,angleY)

    
bus = smbus.SMBus(1)
address = 0x68
bus.write_byte_data(address, power_mqmt_1, 0)



print "CONTROL ACTIVATED"
try:
  while True:
  
    _rotation()
    time.sleep(0.1)
  

 

except KeyboardInterrupt:
  Servo_X.ChangeDutyCycle(7.5)
  Servo_Y.ChangeDutyCycle(7.5)
  time.sleep(0.5)
  Servo_X.stop()
  Servo_Y.stop()
  GPIO.cleanup()
  print "CONTROL DEACTIVATE"




#    for i in range(0,180):
#      angle = 12.5 - angle_increment*i 
#      Servo_X.ChangeDutyCycle(angle)
#      time.sleep(0.05)

#    for i in range(0,180):
#      angle = 2.5 + angle_increment*i 
#      Servo_X.ChangeDutyCycle(angle)
#      time.sleep(0.05)
