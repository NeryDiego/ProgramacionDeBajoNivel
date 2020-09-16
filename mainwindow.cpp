#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFile>
#include <QTextStream>
#include <QMessageBox>
#include <QPixmap>

/*
 * VARIABLES GLOBALES & DEFINES
 */
#define MAXTIMINGS	85
#define DHTPIN		3 //GPIO 22
#define Enfriamiento 0 //GPIO 17
#define Calentamiento 2 //GPIO 27
#define Riego 1 //GPIO 18 (PWM)
#define InicialPWM 0
#define RangoPWM 100
int dht11_dat[5] = { 0, 0, 0, 0, 0 };
int flagStart = 0;
int tempdeseada = 0;
int humedeseada = 0;
int maxpoweract = 0;
/*****************************************/
MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow)
{
    ui->setupUi(this);
    //Configuración elementos mainwindow
    ui->lcd_humidity->setPalette(Qt::blue);
    ui->lcd_temperature->setPalette(Qt::green);
    ui->lcdstart->setPalette(Qt::red);
    ui->pushButton->setText("Start");
    //Configuración Slider y sus LCD
    ui->tempSlider->setRange(0,40);
    ui->humSlider->setRange(0,100);
    ui->lcdTempDes->setPalette(Qt::black);
    ui->lcdHumDes->setPalette(Qt::black);
    //Para utilizar WiringPi
    wiringPiSetup();
    //Configuración Pines
    pinMode(Enfriamiento, OUTPUT);
    pinMode(Calentamiento, OUTPUT);
    //Configuracion PWM
    softPwmCreate(Riego, InicialPWM, RangoPWM);
    //Configuración para el sensor DHT11    
    QTimer *timerSensor = new QTimer(this);
    connect(timerSensor,SIGNAL(timeout()),this, SLOT(DHT11Reading()));
    timerSensor->start(10); //

}

MainWindow::~MainWindow()
{
    delete ui;
}
//UpdateTxT actualiza el archivo txt que leera el codigo de Python
void MainWindow::UpdateTxT(int Temp, int hum){
    //Constructor
    QFile file("/home/pi/ProgramacionDeBajoNivel/ProyectoFinal/HMI_Invernadero/HMI_Invernadero/ValoresApp.txt");
    //This is to check if the file is open or not
    if (!file.open(QFile::WriteOnly | QFile::Text)){
        QMessageBox::warning(this,"title", "file not open");
    }

    //To write inside the file, we need an object of QTextStream
    QTextStream write(&file);
    QString TextToWrite_temp = QString::number(Temp);
    QString TextToWrite_hum = QString::number(hum);
    write << TextToWrite_temp;
    write << TextToWrite_hum;
    file.flush();
    file.close();
}
//Lee el archivo TxT modificado por Python para saber si el usuario hizo alguna modificacion
void MainWindow::ReadTxT(){
    QFile file("/home/pi/ProgramacionDeBajoNivel/ProyectoFinal/HMI_Invernadero/HMI_Invernadero/RespuestaAWS.txt");

    QString line;
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)){
        QTextStream stream(&file);
        while (!stream.atEnd()){
            line.append(stream.readLine());
        }
        QString RespuestaAWS = line;
        //Dependiendo de la respuesta del usuario el sistema se apaga o el pwm se pone al 100%
        if(RespuestaAWS == "Stop"){
            flagStart = 0;
            ui->lcdstart->display(flagStart);

        } else if (RespuestaAWS == "MaxPower") {
            maxpoweract = 20;
            softPwmWrite(Riego,100);
        }
    }
    file.close();
    if (!file.open(QFile::WriteOnly | QFile::Text)){
        QMessageBox::warning(this,"title", "file not open");
    }

    //To write inside the file, we need an object of QTextStream
    //Una vez leido el archivo lo sobreescribimos para dejarlo vacio
    QTextStream write(&file);
    QString TextToWriteEmpty = "";
    write << TextToWriteEmpty;
    file.flush();
    file.close();
}
//Funcion que realiza la lectura del sensor de Temperatura y Humedad
void MainWindow::DHT11Reading(){
    if (flagStart == 1){
        uint8_t laststate	= HIGH;
        uint8_t counter		= 0;
        uint8_t j		= 0, i;
        float	f; /* fahrenheit */

        //Para la lectura del DHT11
        dht11_dat[0] = dht11_dat[1] = dht11_dat[2] = dht11_dat[3] = dht11_dat[4] = 0;

        /* pull pin down for 18 milliseconds */
        pinMode( DHTPIN, OUTPUT );
        digitalWrite( DHTPIN, LOW );
        delay( 18 );
        /* then pull it up for 40 microseconds */
        digitalWrite( DHTPIN, HIGH );
        delayMicroseconds( 40 );
        /* prepare to read the pin */
        pinMode( DHTPIN, INPUT );

        /* detect change and read data */
        for ( i = 0; i < MAXTIMINGS; i++ )
        {
            counter = 0;
            while ( digitalRead( DHTPIN ) == laststate )
            {
                counter++;
                delayMicroseconds( 1 );
                if ( counter == 255 )
                {
                    break;
                }
            }
            laststate = digitalRead( DHTPIN );

            if ( counter == 255 )
                break;

            /* ignore first 3 transitions */
            if ( (i >= 4) && (i % 2 == 0) )
            {
                /* shove each bit into the storage bytes */
                dht11_dat[j / 8] <<= 1;
                if ( counter > 16 )
                    dht11_dat[j / 8] |= 1;
                j++;
            }
        }

        /*
         * check we read 40 bits (8bit x 5 ) + verify checksum in the last byte
         * print it out if data is good
         */
        if ( (j >= 40) &&
             (dht11_dat[4] == ( (dht11_dat[0] + dht11_dat[1] + dht11_dat[2] + dht11_dat[3]) & 0xFF) ) )
        {
            f = dht11_dat[2] * 9. / 5. + 32;

            int h = dht11_dat[0] + dht11_dat[1];
            int c = dht11_dat[2] + dht11_dat[3];
            //Mostramos la temperatura y la humedad
            tempdeseada = ui->tempSlider->value();
            humedeseada = ui->humSlider->value();
            //Dependiendo de la diferencia de temperatura se decide si se prende el
            //sistema de enfriamiento o el sistema de calentamiento
            int diferencia_temp = tempdeseada - c;

            if(diferencia_temp > 0){
                digitalWrite(Calentamiento, HIGH);
                digitalWrite(Enfriamiento, LOW);
            } else if (diferencia_temp < 0) {
                digitalWrite(Enfriamiento, HIGH);
                digitalWrite(Calentamiento, LOW);
            } else {
                digitalWrite(Calentamiento, LOW);
                digitalWrite(Enfriamiento, LOW);
            }
            //Si el usuario coloco el sistema a maxima potencia entonces el pwm trabaja al 100%
            if(maxpoweract == 0){
                int diferencia_hume = humedeseada - h;
                if(diferencia_hume <= 0){
                    softPwmWrite(Riego, 0);
                } else if (diferencia_hume > 100){
                    softPwmWrite(Riego, 100);
                } else {
                    softPwmWrite(Riego, diferencia_hume);
                }
            } else {
                maxpoweract = maxpoweract - 1;
            }
            ui->lcd_temperature->display(int(c));
            ui->lcd_humidity->display(int(h));
            UpdateTxT(c, h);
            ReadTxT();
            ui->label_7->setText(QString::number(maxpoweract));
        }

    } else {
        ui->pushButton->setText("Start");
        ui->lcd_humidity->display(0.0);
        ui->lcd_temperature->display(0.0);
        softPwmWrite(Riego, 0);
        digitalWrite(Calentamiento, LOW);
        digitalWrite(Enfriamiento, LOW);
    }
}

void MainWindow::on_pushButton_clicked()
{
    if (flagStart == 0){
        flagStart = 1;
        ui->pushButton->setText("Stop");
    } else {
        flagStart = 0;
        ui->pushButton->setText("Start");
        UpdateTxT(0,0);
    }
    ui->lcdstart->display(flagStart);
}
