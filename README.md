# MindTV App

Este projeto consiste em um sistema para coletar, treinar e prever emoções baseadas em dados fisiológicos utilizando sensores GSR e cardíacos. O sistema está dividido em três abas principais: Coleta Inicial, Treinamento da Rede e MindTV App.

## Instalação

1. Clone o repositório:
    ```bash
    git clone https://github.com/seu-usuario/MindTV-app.git
    cd MindTV-app
    ```

2. Crie um ambiente virtual e ative-o:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/Mac
    venv\Scripts\activate  # Windows
    ```

3. Instale as dependências necessárias:
    ```bash
    pip install -r requirements.txt
    ```

4. Certifique-se de que os módulos necessários estão instalados:
    ```bash
    pip install pyqt5 pandas scikit-learn joblib pyserial
    ```

## Uso

### Coleta Inicial

1. Selecione a porta serial onde os sensores estão conectados.
2. Defina o tempo de coleta (em minutos) das coletas.
3. Clique em "Iniciar Coleta" para começar a coletar os dados dos sensores.
4. Visualize os dados coletados na barra de log e acompanhe o progresso da coleta através da barra de progresso.
5. Após a coleta, clique em "Exportar CSV" para salvar os dados coletados em um arquivo CSV.
6. Clique em "Próxima aba" para avançar para a aba de Treinamento da Rede.

### Treinamento da Rede

1. Importe o CSV gerado na etapa de coleta inicial. Você pode importar até 5 arquivos CSV diferentes.
2. Clique em "Treinar Modelo" para iniciar o treinamento do modelo com base nos dados importados.
3. O modelo será treinado para prever emoções com base nos dados de batimentos cardíacos, média de batimentos e GSR.
4. Após o treinamento, o modelo será salvo como `trained_model.joblib`.
5. Clique em "Próxima aba" para avançar para a aba MindTV App.

### MindTV App

1. Selecione a porta serial onde os sensores estão conectados.
2. Defina o tempo de coleta (em minutos) das coletas.
3. Clique em "Iniciar Coleta" para começar a coletar os dados dos sensores em tempo real.
4. Visualize os dados coletados na barra de log e acompanhe o progresso da coleta através da barra de progresso.
5. Acompanhe o gráfico de emoções em tempo real.
6. Após a coleta, clique em "Previsão de Emoção" para prever a emoção predominante com base nos dados coletados em tempo real utilizando o modelo treinado.
7. O resultado da previsão será exibido na barra de log e em uma janela de diálogo.

## Código do Arduino

Conecte os sensores GSR e cardíacos ao Arduino Mega conforme as instruções abaixo:

```cpp
#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"

MAX30105 particleSensor;

const byte RATE_SIZE = 4;
byte rates[10][RATE_SIZE];
byte rateSpot[10];
long lastBeat[10];
float beatsPerMinute[10];
int beatAvg[10];

void setup() {
  Serial.begin(115200);

  for (int i = 0; i < 10; i++) {
    rateSpot[i] = 0;
    lastBeat[i] = 0;
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
      Serial.println("MAX30105 not found. Please check wiring/power.");
      while (1);
    }
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);
  }
}

void loop() {
  for (int i = 0; i < 10; i++) {
    long irValue = particleSensor.getIR();
    int GSR = analogRead(i); // Assume GSR sensors are connected to A0-A9

    if (checkForBeat(irValue)) {
      long delta = millis() - lastBeat[i];
      lastBeat[i] = millis();
      beatsPerMinute[i] = 60 / (delta / 1000.0);

      if (beatsPerMinute[i] < 255 && beatsPerMinute[i] > 20) {
        rates[i][rateSpot[i]++] = (byte)beatsPerMinute[i];
        rateSpot[i] %= RATE_SIZE;
        beatAvg[i] = 0;
        for (byte x = 0; x < RATE_SIZE; x++) {
          beatAvg[i] += rates[i][x];
        }
        beatAvg[i] /= RATE_SIZE;
      }
    }
    Serial.print((int)beatsPerMinute[i]);
    Serial.print(",");
    Serial.print(beatAvg[i]);
    Serial.print(",");
    Serial.print(GSR); // GSR
    Serial.print(",");
  }
  Serial.println();
  delay(20); // Small delay to avoid overwhelming the serial buffer
}
