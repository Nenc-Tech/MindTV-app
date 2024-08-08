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

    def __init__(self, model, data):
        super().__init__()
        self.model = model
        self.data = data

    def run(self):
        try:
            df = pd.DataFrame(self.data, columns=['beatsPerMinute', 'beatAvg', 'GSR'])
            predictions = self.model.predict(df)
            prediction_counts = pd.Series(predictions).value_counts()
            most_common = prediction_counts.idxmax()
            result_message = f"Tipo de conteúdo previsto: {most_common}"
            self.prediction_signal.emit(result_message)
            self.log_signal.emit(result_message)
        except Exception as e:
            self.log_signal.emit(f"Erro durante a previsão: {str(e)}")

class TrainingThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        try:
            dfs = []
            for file_path in self.file_paths:
                if file_path:
                    df = pd.read_csv(file_path)
                    if 'Content' not in df.columns:
                        self.log_signal.emit(f"Erro: o arquivo {file_path} não contém a coluna 'Content'.")
                        return
                    dfs.append(df)
            data = pd.concat(dfs, ignore_index=True)
            X = data[['beatsPerMinute', 'beatAvg', 'GSR']]
            y = data['Content']
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            dump(model, 'trained_model.joblib')
            self.log_signal.emit("Treinamento concluído e modelo salvo como 'trained_model.joblib'.")
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

        self.import_buttons = []
        for i in range(5):
            import_button = QPushButton(f'Selecionar arquivo CSV {i+1}', self)
            import_button.clicked.connect(lambda _, x=i: self.import_csv(x))
            layout.addWidget(import_button)
            self.import_buttons.append(import_button)

        self.train_button = QPushButton('Treinar Modelo', self)
        self.train_button.clicked.connect(self.train_model)
        layout.addWidget(self.train_button)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.next_button = QPushButton('Próxima aba', self)
        self.next_button.clicked.connect(self.next_tab)
        self.next_button.setEnabled(False)
        layout.addWidget(self.next_button)

        self.setLayout(layout)
        self.setWindowTitle('Treinamento da Rede')

        self.file_paths = [None] * 5

    def import_csv(self, index):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            self.file_paths[index] = file_path
            self.output.append(f"Arquivo {index+1} selecionado: {file_path}")

    def train_model(self):
        if not any(self.file_paths):
            self.output.append("Erro: pelo menos um arquivo CSV deve ser selecionado.")
            return
        self.output.append("Iniciando o treinamento do modelo...")
        self.train_button.setEnabled(False)
        self.training_thread = TrainingThread(self.file_paths)
        self.training_thread.log_signal.connect(self.log_output)
        self.training_thread.start()

    def log_output(self, message):
        self.output.append(message)

    def next_tab(self):
        self.parent().setCurrentIndex(2)

class MainApp(QTabWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.coleta_inicial_widget = ColetaInicialWidget()
        self.treinamento_rede_widget = TreinamentoRedeWidget()
        self.predicao_widget = PredicaoWidget()
        
        self.addTab(self.coleta_inicial_widget, "Coleta Inicial")
        self.addTab(self.treinamento_rede_widget, "Treinamento da Rede")
        self.addTab(self.predicao_widget, "Predição")

        self.setWindowTitle('MindTV App')
        self.show()

class PredicaoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.import_button = QPushButton('Selecionar arquivo CSV para Predição', self)
        self.import_button.clicked.connect(self.import_csv)
        layout.addWidget(self.import_button)

        self.predict_button = QPushButton('Realizar Predição', self)
        self.predict_button.clicked.connect(self.predict)
        layout.addWidget(self.predict_button)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)
        self.setWindowTitle('Predição')

        self.file_path = None
        self.model = None

    def import_csv(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)
        if file_path:
            self.file_path = file_path
            self.output.append(f"Arquivo selecionado: {file_path}")

    def predict(self):
        if not self.file_path:
            self.output.append("Erro: selecione um arquivo CSV para predição.")
            return
        if not os.path.exists('trained_model.joblib'):
            self.output.append("Erro: modelo treinado não encontrado.")
            return
        self.output.append("Iniciando a predição...")
        self.predict_button.setEnabled(False)
        self.model = load('trained_model.joblib')
        data = pd.read_csv(self.file_path)
        if 'beatsPerMinute' not in data.columns or 'beatAvg' not in data.columns or 'GSR' not in data.columns:
            self.output.append("Erro: o arquivo CSV deve conter as colunas 'beatsPerMinute', 'beatAvg' e 'GSR'.")
            self.predict_button.setEnabled(True)
            return
        self.prediction_thread = PredictionThread(self.model, data[['beatsPerMinute', 'beatAvg', 'GSR']].values.tolist())
        self.prediction_thread.log_signal.connect(self.log_output)
        self.prediction_thread.prediction_signal.connect(self.show_prediction)
        self.prediction_thread.start()

    def log_output(self, message):
        self.output.append(message)

    def show_prediction(self, prediction):
        self.output.append(prediction)
        self.predict_button.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApp()
    sys.exit(app.exec_())
