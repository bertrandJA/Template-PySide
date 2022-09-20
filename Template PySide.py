import sys, logging, traceback
import time #os, time, datetime, pandas as pd
from PySide6 import QtCore, QtWidgets, QtGui

LOGGING_LEVEL = logging.INFO #DEBUG, INFO, WARNING, ERROR, CRITICAL #Level of verbosity of logs
VERSION = "2022-09-09"
HELP_TEXT = """This program is a template with just a help menu, a button launching a backround task, and a progress bar"""

class WorkerSignals(QtCore.QObject): #Generic class defining signals available for a Worker in a thread
    result = QtCore.Signal(object)  #Emitted if no error occurs
    progress = QtCore.Signal(int) #will be implemented via a callback function. Emitted to track progress.
    error = QtCore.Signal(tuple) #Emitted if an error is thrown
    finished = QtCore.Signal() #Emitted regardless of whether there is an error or not

class Worker(QtCore.QRunnable): #Generic class to build a worker. Will be used for all backend operations
    def __init__(self, fn, *args, **kwargs): #Create a worker to launch fn in a thread
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals() #Define signals
        self.kwargs['progress_callback'] = self.signals.progress #Add the callback to track progress to our kwargs

    @QtCore.Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs) #Call fn, with kwargs (including the callback for progress)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  #Return the result of the processing
        finally:
            self.signals.finished.emit()

class ui_MainWindow(QtWidgets.QMainWindow): #Bare user interface without any logic attached to widgets
    def __init__(self, ):
        super().__init__()
        self.setWindowTitle(f"My Application, version {VERSION}")
        menu = self.menuBar() #There can only be a unique menu
        toolbar = QtWidgets.QToolBar("My main toolbar") #There may be several toolbars
        self.addToolBar(toolbar)
        self.statusBar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusBar)

        file_menu = menu.addMenu("&File") #Add a sub-menu
        self.save_action = QtGui.QAction("&Save", self)
        self.save_action.setStatusTip("This is not implemented in this template") #Tip displayed in status bar when we hover on action
        file_menu.addAction(self.save_action)   #Add action is sub-menu File

        self.help_action = QtGui.QAction("&Help", self)
        #self.help_action.setIcon(QtGui.QIcon.fromTheme("help-contents")) #https://specifications.freedesktop.org/icon-naming-spec/icon-naming-spec-latest.html

        pixmapi = QtWidgets.QStyle.StandardPixmap.SP_TitleBarContextHelpButton #standard  help icon
        icon = self.style().standardIcon(pixmapi)
        self.help_action.setIcon(icon)
        #https://srinikom.github.io/pyside-docs/PySide/QtGui/QStyle.html#PySide.QtGui.PySide.QtGui.QStyle.StandardPixmap
        self.help_action.setStatusTip("Will display help")  #Tip displayed in status bar when we hover on action
        #A same action can be added both to a menu, a toolbar, a contextual menu, ...
        menu.addAction(self.help_action)    #Add action directly in menu
        toolbar.addAction(self.help_action)

        self.helpText = QtWidgets.QPlainTextEdit(HELP_TEXT)
        self.helpText.setWindowTitle("Help")
        self.helpText.setReadOnly(True)
        self.helpText.setMinimumSize(650, 350)

        central_widget = QtWidgets.QWidget()
        central_widget.setMinimumSize(700, 400)
        central_layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        self.action_button = QtWidgets.QPushButton("Launch Action")
        self.action_button.setFixedWidth(120)
        self.action_button.setStatusTip("Will launch an action")
        central_layout.addWidget(self.action_button, stretch=0)

        self.progress_group = QtWidgets.QGroupBox("Progress:")
        progress_layout = QtWidgets.QHBoxLayout()
        self.progress_label = QtWidgets.QLabel("Progress of step x:")
        self.progress_bar = QtWidgets.QProgressBar()
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.cancel_button)
        self.progress_group.setLayout(progress_layout)
        central_layout.addWidget(self.progress_group, stretch=0)
        self.progress_group.hide() #At startup, progress is hidden

        central_layout.addStretch() #allows window to stretch without affecting widgets

class MainWindow(ui_MainWindow): #Adds logic to the interface widgets
    def __init__(self, xxx):
        logging.info(f"Launching program version {VERSION}")
        super().__init__()
        self.cancel_flag = False #Flag that will be triggered if user chooses to cancels a background job via cancel_button
        self.threadpool = QtCore.QThreadPool() #Pool for workers threads that will perform background tasks
        self.help_action.triggered.connect(lambda x: self.helpText.show())
        self.action_button.clicked.connect(self.launch_action_f)
        self.cancel_button.clicked.connect(lambda x: setattr(self, "cancel_flag", True)) #Signal to interrupt progress

    def initiate_new_step(self, text="Launching...", minimum=0, maximum=100):   #Initia
        self.action_button.setEnabled(False) #Disable action button
        self.progress_group.show()  #Show progress
        self.progress_label.setText(text)
        self.progress_bar.setRange(minimum, maximum)
        self.setProgress(minimum)

    def setProgress(self, value):
        self.progress_bar.setValue(value)

    @QtCore.Slot()
    def launch_action_f(self):
        self.initiate_new_step("Progress of Step 1:", 1, 50)
        self.cancel_flag = False #reset cancel flag if needed
        self.worker_action = Worker(self.launch_action_b)
        self.worker_action.signals.progress.connect(self.launch_action_b_progress)
        self.worker_action.signals.result.connect(self.launch_action_b_result)
        self.worker_action.signals.error.connect(self.launch_action_b_error)
        self.worker_action.signals.finished.connect(self.launch_action_b_finished)
        self.threadpool.start(self.worker_action)

    def launch_action_b(self, progress_callback):
        logging.debug("Action launched in a background thread")
        for i in range(50):
            if self.cancel_flag: #Test if user clicked on cancel_button
                raise KeyboardInterrupt("Action canceled by user")
            time.sleep(0.1)
            self.worker_action.signals.progress.emit(i)
        return i+1

    def launch_action_b_progress(self, count):
        logging.debug(f"Now at step {count}")
        self.setProgress(count)

    def launch_action_b_result(self, result):
        logging.info(f"Action performed {result} steps without error")

    def launch_action_b_error(self, error_tuple):
        logging.error("Action in error")

    def launch_action_b_finished(self):
        logging.debug("Action in background finished")
        self.progress_group.hide() #Hide progress
        self.action_button.setEnabled(True) #Enable button since task is finished
        self.statusBar.showMessage("Ready for next action")

def main():
    app = QtWidgets.QApplication(sys.argv) #Launch Qt
    myWindow = MainWindow("xxx") #Create graphical interface
    myWindow.show() #display window
    sys.exit(app.exec()) #Launch Qt, and exit properly when window is closed

if __name__ == '__main__':
    logging.basicConfig(level=LOGGING_LEVEL, format="{asctime} {message}", style="{", datefmt="%H:%M:%S") #Format logging messages
    main()