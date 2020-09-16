import socket
import select
import time
from threading import Thread
import sqlite3
import boto3
from twilio.rest import Client
import datetime
# client credentials are read from TWILIO_ACCOUNT_SID and AUTH_TOKEN
client = Client()

# this is the Twilio sandbox testing number
from_whatsapp_number='whatsapp:+14155238886'
# replace this number with your own WhatsApp Messaging number
to_whatsapp_number='whatsapp:+5213314798479'
print("All Modules Loaded ...... ")

class SocketServer(Thread):
    def __init__(self, host = '192.168.1.79', port = 1100, max_clients = 2):
        """ Initialize the server with a host and port to listen to.
        Provide a list of functions that will be used when receiving specific data """
        Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.host = host
        self.port = port
        self.sock.bind((host, port))
        self.sock.listen(max_clients)
        self.sock_threads = []
        self.counter = 0 # Will be used to give a number to each thread

    def close(self):
        """ Close the client socket threads and server socket if they exists. """
        print('Closing server socket (host {}, port {})'.format(self.host, self.port))

        for thr in self.sock_threads:
            thr.stop()
            thr.join()

        if self.sock:
            self.sock.close()
            self.sock = None

    def run(self):
        """ Accept an incoming connection.
        Start a new SocketServerThread that will handle the communication. """
        print('Starting socket server (host {}, port {})'.format(self.host, self.port))

        self.__stop = False
        while not self.__stop:
            self.sock.settimeout(1)
            try:
                client_sock, client_addr = self.sock.accept()
            except socket.timeout:
                client_sock = None

            if client_sock:
                client_thr = SocketServerThread(client_sock, client_addr, self.counter)
                self.counter += 1
                self.sock_threads.append(client_thr)
                client_thr.start()
        self.close()

    def stop(self):
        self.__stop = True


class SocketServerThread(Thread):
    def __init__(self, client_sock, client_addr, number):
        """ Initialize the Thread with a client socket and address """
        Thread.__init__(self)
        self.client_sock = client_sock
        self.client_addr = client_addr
        self.number = number

    def run(self):
        print("[Thr {}] SocketServerThread starting with client {}".format(self.number, self.client_addr))
        self.__stop = False
        while not self.__stop:
            if self.client_sock:
                # Check if the client is still connected and if data is available:
                try:
                    rdy_read, rdy_write, sock_err = select.select([self.client_sock,], [self.client_sock,], [], 5)
                except select.error as err:
                    print('[Thr {}] Select() failed on socket with {}'.format(self.number,self.client_addr))
                    self.stop()
                    return

                if len(rdy_read) > 0:
                    read_data = self.client_sock.recv(1024)

                    # Check if socket has been closed
                    if len(read_data) == 0:
                        print('[Thr {}] {} closed the socket.'.format(self.number, self.client_addr))
                        self.stop()
                    else:
                        global flag
                        global counter
                        global uppload
                        global sensor_flag
                        global inroom
                        global messageFlag
                        if read_data > '00':
                            stringdata = read_data.decode('utf-8')                        
                            try:
                                result = stringdata.index('.')
                                newstrindata = stringdata[0:result]
                                intdata = int(newstrindata)
                            except ValueError:    
                                intdata = int(stringdata)

                        if intdata > 470:              
                          uppload = uppload + 1
                          if inroom == 1:
                              ubicacion = 'Posicion dentro del cuarto'
                          else:
                              ubicacion = 'Posicion fuera del cuarto'
                              
                          if flag == 1:
                              counter = counter + 1
                              
                          if intdata > 10000 and messageFlag == 0:
                              print 'Usuario en peligro'
                              
                              client.messages.create(body='Alert! La persona puede haber sufrido una caida',
                                   from_=from_whatsapp_number,
                                   to=to_whatsapp_number)
                              alerta = 'Se envio una senal de auxilio'
                              AWS_Main(intdata, ubicacion,sensor_flag, alerta)
                              alerta = ''
                              messageFlag = 1
                              
                        elif intdata == 1:
                          flag = 1
                          counter = 1
                          uppload = 0
                          sensor_flag = 1
                          if inroom == 1:
                              inroom = 0 #inroom = 0 --> Ubicacion fuera
                          else:
                              inroom = 1 #inroom = 1 --> Ubicacion dentro
                        elif intdata < 471:
                          #print('[Thr {}] Posicion afuera del cuarto {}'.format(self.number, read_data.rstrip()))                                            
                          uppload = uppload + 1
                          if inroom == 1:
                              ubicacion = 'Posicion dentro del cuarto'
                          else:
                              ubicacion = 'Posicion fuera del cuarto'
                          if flag == 1:
                              counter = counter + 1

                        if (flag == 1 and counter > 1) or (uppload == 100):
                          db_conector = sqlite3.connect('log-usuario.db')
                          db_cursor = db_conector.cursor()
                          db_cursor.execute("INSERT INTO posicion values(datetime('now', 'localtime'), (?), (?), (?))", (read_data+' cm',ubicacion ,sensor_flag))
                          db_conector.commit()
                          db_conector.close()
                          alerta = '--------'
                          AWS_Main(intdata, ubicacion,sensor_flag,alerta)
                          flag = 0
                          counter = 0
                          sensor_flag = 0
                          uppload = 0 #Con la configuracion actual el Photon manda informacion (RSSI) cada 100 ms
                          messageFlag = 0
                          
                          
            else:
                print("[Thr {}] No client is connected, SocketServer can't receive data".format(self.number))
                self.stop()
        self.close()

    def stop(self):
        self.__stop = True

    def close(self):
        """ Close connection with the client socket. """
        if self.client_sock:
            print('[Thr {}] Closing connection with {}'.format(self.number, self.client_addr))
            self.client_sock.close()
            #Functions for AWS - DynamoDB
class MyDb(object):

    def __init__(self, Table_Name='Posicionamiento'):
        self.Table_Name=Table_Name

        self.db = boto3.resource('dynamodb')
        self.table = self.db.Table(Table_Name)

        self.client = boto3.client('dynamodb')

    @property
    def get(self):
        response = self.table.get_item(
            Key={
                'Person_ID':"1"
            }
        )

        return response

    def put(self, Person_ID='' , Localizacion='', distanciacm='', sensor='', fecha='', alerta=''):
        self.table.put_item(
            Item={
                'Person_ID':Person_ID,
                'Localizacion':Localizacion,
                'Distancia_cm' :distanciacm,
                'Sensor_Flag' : sensor,
                'Fecha_Evento': fecha,
                'Alerta': alerta
            }
        )

    def delete(self,Sensor_ID=''):
        self.table.delete_item(
            Key={
                'Person_ID': Person_ID
            }
        )

    def describe_table(self):
        response = self.client.describe_table(
            TableName='Person'
        )
        return response

    @staticmethod
    def sensor_value(distance, ubicacion,sensor_flag,alerta):

       
        distanciacm, localizacion,sensor, fecha, alerta = distance, ubicacion,sensor_flag, datetime.datetime.now(), alerta

        return localizacion, distanciacm, sensor, fecha,alerta


def AWS_Main(distance, ubicacion,sensor_flag,alerta):
    global awsId
    obj = MyDb()
    Localizacion , distanciacm, sensor, fecha, alerta= obj.sensor_value(distance, ubicacion,sensor_flag,alerta)
    obj.put(Person_ID=str(awsId), Localizacion=str(Localizacion), distanciacm=str(distanciacm),sensor=str(sensor), fecha=str(fecha), alerta=str(alerta))
    awsId = awsId + 1
    #print("Uploaded Sample on Cloud T:{},H{} " + distanciacm)
    
def main():
    # Start socket server, stop it after a given duration
    duration = 1 * 30 #duration = mins * 60 (segundos), runtime of the program
    #3600 segs = 1 hora
    server = SocketServer()
    server.start()
    time.sleep(duration)
    server.stop()
    server.join()
    print('End.')
    
if __name__ == "__main__":
    global flag
    global counter
    global uppload
    global sensor_flag
    global inroom
    global messageFlag
    global awsId
    awsId = 0
    messageFlag = 0
    inroom = 1
    sensor_flag = 0
    counter = 0
    uppload = 0
    flag = 0
    main()   
