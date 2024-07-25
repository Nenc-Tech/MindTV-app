from builtins import Exception, float, int, len, list, range, str, super
import os
import sys
import pandas as pd
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox,
    QTextEdit, QSpinBox, QProgressBar, QDialog, QHBoxLayout, QTabWidget, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal
from joblib import load, dump
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

class DataCollectionThread(QThread):
    log_signal = pyqtSignal(str)
    data_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int)

    def __init__(self, port, duration):
        super().__init__()
        self.port = port
        self.duration = duration
        self.collecting = True

    def run(self):
        try:
            ser = serial.Serial(self.port, 115200)
            collected_data = []
            start_time = pd.Timestamp.now()
            while (pd.Timestamp.now() - start_time).seconds < self.duration:
                data = ser.readline().decode('utf-8').strip()
                self.log_signal.emit(data)
                data_split = data.split(',')
                if len(data_split) == 4:
                    collected_data.append([float(data_split[1]), float(data_split[2]), float(data_split[3])])  # Ignoring irValue
                elapsed_time = (pd.Timestamp.now() - start_time).seconds
                progress = int((elapsed_time / self.duration) * 100)
                self.progress_signal.emit(progress)
            self.data_signal.emit(collected_data)
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

        self.content_label = QLabel("Tipo de Conteúdo Assistido:")
        layout.addWidget(self.content_label)

        self.content_combo = QComboBox(self)
        self.content_combo.addItems([
            "Programa esportivo", "Programa jornalistico", "Programa politico", "Filme de acao", "Filme de comedia", 
            "Filme de terror", "Serie de drama", "Programa de musica", "Serie de comedia", "Serie de acao", 
            "Reality show", "Documentario", "Desenho animado", "Programa de culinaria", "Programa de viagem", 
            "Programa de entrevistas", "Serie de ficcao cientifica", "Programa de variedade", "Programa infantil", 
            "Minisserie", "Filme de romance", "Serie de suspense", "Programa de auditorio", "Programa de reformas", 
            "Programa de talentos", "Filme de aventura", "Filme de fantasia", "Serie de misterio", 
            "Programa de saude e bem-estar", "Telejornal", "Novela", "Programa de tecnologia", 
            "Programa de natureza e vida selvagem", "Talk show", "Programa de moda e estilo", "Filme historico", 
            "Serie policial", "Programa de quiz e jogos", "Serie documental", "Programa de debates", 
            "Programa de espiritualidade/religiao", "Filme de animacao", "Serie antologica"
        ])
        layout.addWidget(self.content_combo)

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
        self.data_collection_thread.start()

    def log_output(self, message):
        self.output.append(message)

    def store_data(self, data):
        self.data = data
        self.export_button.setEnabled(True)
        self.collect_button.setEnabled(True)
        self.output.append("Coleta de dados armazenada.")

    def export_csv(self):
        try:
            df = pd.DataFrame(self.data, columns=['beatsPerMinute', 'beatAvg', 'GSR'])
            content_type = self.content_combo.currentText()
            df['Content'] = content_type

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
        if not self.file_paths[0]:
            self.output.append("Erro: pelo menos um arquivo CSV deve ser selecionado.")
            return
        self.output.append("Iniciando o treinamento do modelo...")
        self.train_button.setEnabled(False)
        self.training_thread = TrainingThread(self.file_paths)
        self.training_thread.log_signal.connect(self.log_output)
        self.training_thread.start()

    def log_output(self, message):
        self.output.append(message)
        self.train_button.setEnabled(True)

class PredictionResultDialog(QDialog):
    def __init__(self, message):
        super().__init__()
        self.setWindowTitle("Resultado da Previsão")
        layout = QVBoxLayout()
        self.label = QLabel(message)
        layout.addWidget(self.label)
        self.setLayout(layout)

class MindTVAppWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.port_label = QLabel("Selecione a Porta Serial:")
        layout.addWidget(self.port_label)

        self.port_combo = QComboBox(self)
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        layout.addWidget(self.port_combo)

        self.duration_label = QLabel("Selecione a duração da coleta (minutos):")
        layout.addWidget(self.duration_label)

        self.duration_spin = QSpinBox(self)
        self.duration_spin.setRange(1, 5)
        layout.addWidget(self.duration_spin)

        self.collect_button = QPushButton('Iniciar Coleta', self)
        self.collect_button.clicked.connect(self.collect_data)
        layout.addWidget(self.collect_button)

        self.predict_button = QPushButton('Previsão de Conteúdo', self)
        self.predict_button.clicked.connect(self.predict_content)
        self.predict_button.setEnabled(False)
        layout.addWidget(self.predict_button)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.setLayout(layout)
        self.setWindowTitle('MindTV App')
        self.show()

    def get_selected_port(self):
        return self.port_combo.currentText()

    def get_duration(self):
        return self.duration_spin.value()

    def collect_data(self):
        port = self.get_selected_port()
        duration = self.get_duration() * 60  # Convert to seconds
        self.output.append(f"Iniciando coleta de dados na porta {port} por {self.get_duration()} minutos...")

        self.collect_button.setEnabled(False)
        self.data_collection_thread = DataCollectionThread(port, duration)
        self.data_collection_thread.log_signal.connect(self.log_output)
        self.data_collection_thread.data_signal.connect(self.save_data)
        self.data_collection_thread.progress_signal.connect(self.update_progress)
        self.data_collection_thread.start()

    def save_data(self, data):
        df = pd.DataFrame(data, columns=['beatsPerMinute', 'beatAvg', 'GSR'])
        df.to_csv('collected_data.csv', index=False)
        self.output.append("Dados coletados e salvos em collected_data.csv")
        self.collect_button.setEnabled(True)
        self.predict_button.setEnabled(True)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def predict_content(self):
        try:
            model = load('trained_model.joblib')
            data = pd.read_csv('collected_data.csv')
            self.prediction_thread = PredictionThread(model, data)
            self.prediction_thread.log_signal.connect(self.log_output)
            self.prediction_thread.prediction_signal.connect(self.show_prediction_result)
            self.prediction_thread.start()
        except Exception as e:
            self.output.append(f"Erro ao carregar modelo ou dados: {str(e)}")

    def show_prediction_result(self, message):
        dialog = PredictionResultDialog(message)
        dialog.exec_()

    def log_output(self, message):
        self.output.append(message)

class MainApp(QTabWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.coleta_inicial_widget = ColetaInicialWidget()
        self.treinamento_rede_widget = TreinamentoRedeWidget()
        self.mindtv_app_widget = MindTVAppWidget()

        self.addTab(self.coleta_inicial_widget, "Coleta Inicial")
        self.addTab(self.treinamento_rede_widget, "Treinamento da Rede")
        self.addTab(self.mindtv_app_widget, "MindTV App")

        self.setWindowTitle('MindTV App')
        self.resize(800, 600)
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_app = MainApp()
    sys.exit(app.exec_())
