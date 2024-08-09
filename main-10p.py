from builtins import Exception, float, int, len, list, range, str, super
import os
import sys
import pandas as pd
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox,
    QTextEdit, QSpinBox, QProgressBar, QDialog, QTabWidget, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal
from joblib import load, dump
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

class DataCollectionThread(QThread):
    log_signal = pyqtSignal(str)
    data_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int)
    sample_count_signal = pyqtSignal(int)

    def __init__(self, port, duration):
        super().__init__()
        self.port = port
        self.duration = duration
        self.collecting = True
        self.sample_count = 0
        self.collected_data = []

    def run(self):
        try:
            ser = serial.Serial(self.port, 115200)
            start_time = pd.Timestamp.now()
            while (pd.Timestamp.now() - start_time).seconds < self.duration:
                data = ser.readline().decode('utf-8').strip()
                self.log_signal.emit(data)
                data_split = data.split(',')
                if len(data_split) == 3:
                    try:
                        row = [float(data_split[0]), float(data_split[1]), float(data_split[2])]
                        self.collected_data.append(row)
                        self.sample_count += 1
                    except ValueError:
                        self.log_signal.emit(f"Erro ao converter dados: {data}")
                elapsed_time = (pd.Timestamp.now() - start_time).seconds
                progress = int((elapsed_time / self.duration) * 100)
                self.progress_signal.emit(progress)
            self.data_signal.emit(self.collected_data)
            self.sample_count_signal.emit(self.sample_count)
            ser.close()
        except Exception as e:
            self.log_signal.emit(f"Erro durante a coleta de dados: {str(e)}")


class PredictionThread(QThread):
    log_signal = pyqtSignal(str)
    prediction_signal = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            if self.file_path and os.path.exists(self.file_path):
                df = pd.read_csv(self.file_path)
                
                # Verificação se todas as colunas necessárias estão presentes
                if all(col in df.columns for col in ['beatsPerMinute', 'beatAvg', 'GSR']):
                    X_new = df[['beatsPerMinute', 'beatAvg', 'GSR']]
                    
                    # Carregamento do modelo treinado
                    model = load('trained_model.joblib')
                    
                    # Previsão
                    predictions = model.predict(X_new)
                    
                    # Adiciona a coluna de predições ao DataFrame e salva em um novo CSV
                    df['PredictedEmotion'] = predictions
                    output_file = 'predictions.csv'
                    df.to_csv(output_file, index=False)
                    
                    self.log_signal.emit(f"Predições realizadas e salvas em '{output_file}'.")
                else:
                    self.log_signal.emit("Erro: O arquivo não contém todas as colunas necessárias ('beatsPerMinute', 'beatAvg', 'GSR').")
            else:
                self.log_signal.emit(f"Erro: o arquivo {self.file_path} não foi encontrado.")
                
        except Exception as e:
            self.log_signal.emit(f"Erro durante a predição: {str(e)}")

class TrainingThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            file_path = 'dados_base.csv'
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                if 'Emotion' not in df.columns:
                    self.log_signal.emit(f"Erro: o arquivo {file_path} não contém a coluna 'Emotion'.")
                    return
                
                # Separação das features e do label
                X = df[['beatsPerMinute', 'beatAvg', 'GSR']]
                y = df['Emotion']
                
                # Divisão dos dados em treino e teste
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                # Treinamento do modelo
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X_train, y_train)
                
                # Avaliação do modelo
                accuracy = model.score(X_test, y_test)
                self.log_signal.emit(f"Treinamento concluído com acurácia de {accuracy:.2f}.")
                
                # Salvamento do modelo
                dump(model, 'trained_model.joblib')
                self.log_signal.emit("Modelo salvo como 'trained_model.joblib'.")
            else:
                self.log_signal.emit(f"Erro: o arquivo {file_path} não foi encontrado.")
        except Exception as e:
            self.log_signal.emit(f"Erro durante o treinamento: {str(e)}")


class ColetaInicialWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.data = []

    def initUI(self):
        layout = QVBoxLayout()

        self.port_label = QLabel("Selecione a Porta Serial:")
        layout.addWidget(self.port_label)

        self.port_combo = QComboBox(self)
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        layout.addWidget(self.port_combo)

        self.duration_label = QLabel("Tempo de Coleta (minutos):")
        layout.addWidget(self.duration_label)

        self.duration_combo = QComboBox(self)
        self.duration_combo.addItems(["1", "2", "3", "4", "5"])
        layout.addWidget(self.duration_combo)

        self.collect_button = QPushButton('Iniciar Coleta', self)
        self.collect_button.clicked.connect(self.collect_data)
        layout.addWidget(self.collect_button)

        self.export_button = QPushButton('Exportar CSV', self)
        self.export_button.clicked.connect(self.export_csv)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.next_button = QPushButton('Próxima aba', self)
        self.next_button.clicked.connect(self.next_tab)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.sample_count_label = QLabel("Amostras coletadas: 0")
        layout.addWidget(self.sample_count_label)

        self.setLayout(layout)
        self.setWindowTitle('Coleta Inicial')
        self.show()

    def get_selected_port(self):
        return self.port_combo.currentText()

    def get_selected_duration(self):
        return int(self.duration_combo.currentText()) * 60

    def collect_data(self):
        port = self.get_selected_port()
        duration = self.get_selected_duration()
        self.output.append(f"Iniciando coleta de dados na porta {port} por {duration // 60} minutos...")
        self.collect_button.setEnabled(False)

        self.data_collection_thread = DataCollectionThread(port, duration)
        self.data_collection_thread.log_signal.connect(self.log_output)
        self.data_collection_thread.data_signal.connect(self.store_data)
        self.data_collection_thread.progress_signal.connect(self.update_progress)
        self.data_collection_thread.sample_count_signal.connect(self.update_sample_count)
        self.data_collection_thread.start()

    def log_output(self, message):
        self.output.append(message)

    def store_data(self, data):
        if isinstance(data, list) and all(isinstance(i, list) for i in data):
            self.data.extend(data)
        else:
            self.output.append("Erro: Formato de dados inválido.")
            return
        self.export_button.setEnabled(True)
        self.collect_button.setEnabled(True)
        self.next_button.setEnabled(True)
        self.output.append("Coleta de dados armazenada.")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_sample_count(self, count):
        self.sample_count_label.setText(f"Amostras coletadas: {count}")

    def export_csv(self):
        try:
            if not self.data:
                self.output.append("Erro: Nenhum dado para exportar.")
                return
            df = pd.DataFrame(self.data, columns=['beatsPerMinute', 'beatAvg', 'GSR'])
            base_filename = 'coleta_dados'
            extension = '.csv'
            filename = base_filename + extension
            counter = 1
            while os.path.exists(filename):
                filename = f"{base_filename}({counter}){extension}"
                counter += 1
            df.to_csv(filename, index=False)
            self.output.append(f"Dados exportados para {filename}")
        except Exception as e:
            self.output.append(f"Erro ao exportar dados: {str(e)}")

    def next_tab(self):
        self.parent().setCurrentIndex(1)

class TreinamentoRedeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.next_button = QPushButton('Próxima aba', self)
        self.next_button.clicked.connect(self.next_tab)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        self.setLayout(layout)
        self.setWindowTitle('Treinamento da Rede')

        # Inicia o treinamento automático ao carregar o widget
        self.train_model()

    def train_model(self):
        self.output.append("Iniciando treinamento do modelo com 'dados_base.csv'...")
        self.training_thread = TrainingThread()
        self.training_thread.log_signal.connect(self.log_output)
        self.training_thread.start()

    def log_output(self, message):
        self.output.append(message)
        if "Treinamento concluído" in message:
            self.next_button.setEnabled(True)

    def next_tab(self):
        self.parent().setCurrentIndex(2)

class PrevisaoTipoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.file_path = None

    def initUI(self):
        layout = QVBoxLayout()

        self.import_button = QPushButton('Selecionar arquivo CSV para Previsão', self)
        self.import_button.clicked.connect(self.import_csv)
        layout.addWidget(self.import_button)

        self.predict_button = QPushButton('Prever Tipo de Conteúdo', self)
        self.predict_button.clicked.connect(self.predict_content_type)
        self.predict_button.setEnabled(False)
        layout.addWidget(self.predict_button)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)
        self.setWindowTitle('Previsão do Tipo de Conteúdo')

    def import_csv(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            self.file_path = file_path
            self.output.append(f"Arquivo CSV selecionado: {file_path}")
            self.predict_button.setEnabled(True)

    def predict_content_type(self):
        self.output.append("Iniciando previsão do tipo de conteúdo...")
        self.prediction_thread = PredictionThread(self.file_path)
        self.prediction_thread.log_signal.connect(self.log_output)
        self.prediction_thread.start()

    def log_output(self, message):
        self.output.append(message)


class MainApp(QTabWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.coleta_inicial_widget = ColetaInicialWidget()
        self.treinamento_rede_widget = TreinamentoRedeWidget()
        self.predicao_widget = PrevisaoTipoWidget()
        
        self.addTab(self.coleta_inicial_widget, "Coleta Inicial")
        self.addTab(self.treinamento_rede_widget, "Treinamento da Rede")
        self.addTab(self.predicao_widget, "Predição")

        self.setWindowTitle('MindTV App')
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_widget = MainApp()
    main_widget.show()
    sys.exit(app.exec_())