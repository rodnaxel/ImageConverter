#! /usr/bin/python3.6

# Name: imagehex
# Description: This programm to used convert image to hex sequence
# Author: Aleksandr Smirnov (alvonrims@gmail.com)

import sys, os
from fileinput import filename

from PIL import Image

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import inspect


def whoami(param=False):
	""" This is debug function """
	func_info = "L{0}:{1}()".format(*inspect.stack()[1][2:4])
	values = "param={}".format(inspect.getargvalues(inspect.stack()[1][0]).locals)
	return (func_info + " " + values) if param else (func_info)


# I have 4 range of color [0:63], [64:127], [128:191], [192:255]
# format RGBAsp = 00_00_00_00 (8 bit color)
#				   |  |  |  +- "b"
#				   |  |  +---- "g"
#				   |  +------- "r"
#				   +---------- "a"

class ImageHex:
	def __init__(self, filename, mode):
		print(whoami())
		self.img = Image.open(filename).convert(mode)
		self.height, self.width = self.img.size
		self.signal = QtImageHex()

	def _convert_hex(self, rgba):
		r, g, b, a = rgba
		return format((a << 6) | (r << 4) | (g << 2) | b, '#04x')

	def _get_gradient(self, value):
		if (value <= 127):
			return 0 if (value < 63) else 1
		else:
			return 3 if (value > 191) else 2

	def _compress_pixel(self, pixel):
		res = []
		for channel in pixel:
			res.append(self._get_gradient(channel))
		return res

	def compress(self):
		res = []
		for row in range(self.height):
			line = []
			for col in range(self.width):
				pixel = self.img.getpixel((row, col))
				line.append(self._convert_hex(self._compress_pixel(pixel)))
			#TODO: (Fix) Replace qt method in single class
			self.signal.event_progress()
			res.append(line)
		return res

	def get_size(self):
		return self.img.size


def report(seq, filename='output.txt'):
	with open(filename, 'w') as f:
		label = os.path.basename(filename).split(".")[0]
		f.write(label.upper()[:10] + "\n")
		for line in seq:
			s = "\t" + 'db' + ' ' + ",".join(line) + ';' + '\n'
			f.write(s)


class QtImageHex(QtCore.QObject):
	progressed = QtCore.pyqtSignal()

	def __init__(self):
		super(QtImageHex, self).__init__()

	def event_progress(self):
		self.progressed.emit()


class ImageApp(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Image Converter")
		self.setMaximumSize(380, 380)

		self.paths = {'source': '', 'output': ''}
		
		self.image = None
		self.image_mode = "RGBA"
		
		self.seq = []

		self.createUI()

	def createUI(self):
		centralWgt = QWidget(self)
		self.setCentralWidget(centralWgt)
		
		# Create widget <Directories>
		pathbox = QGroupBox("Paths:")
		
		self.lines = dict(source=QLineEdit(), output=QLineEdit())
		for k,v in self.lines.items():
			v.setReadOnly(True)
			v.setDisabled(True)
		
		btnSource = QPushButton("...")
		btnSource.setFixedWidth(30)
		btnSource.setShortcut("ctrl+o")
		btnSource.clicked.connect(self.onOpenImage)

		btnOutput = QPushButton("...")
		btnOutput.setFixedWidth(30)
		btnOutput.clicked.connect(self.onSaveOutput)

		grid = QGridLayout(pathbox)
		grid.setColumnStretch(1,1)

		grid.addWidget(QLabel("Image:"), 0, 0)
		grid.addWidget(self.lines['source'], 0, 1)
		grid.addWidget(btnSource, 0, 2)

		grid.addWidget(QLabel("Text:"), 1, 0)
		grid.addWidget(self.lines['output'], 1, 1)
		grid.addWidget(btnOutput, 1, 2)

		# Create tuner widget
		tbox = QGroupBox("Tuner")
		tbox.setCheckable(True)
		tbox.setChecked(False)
		tbox_layout = QHBoxLayout(tbox)

		self.sliders = {}
		for name in ('r', 'g', 'b', 'a'):
			vbox = QVBoxLayout()
			slider = QSlider(tbox)
			slider.setFixedHeight(100)
			slider.setRange(0,3)
			slider.setTickPosition(QSlider.TicksBothSides)
			self.sliders[name] = slider
			
			vbox.addWidget(QLabel(name), QtCore.Qt.AlignTop)
			vbox.addWidget(slider, QtCore.Qt.AlignLeft)
			tbox_layout.addLayout(vbox)

		# Buttons
		btn_widget = QWidget(self)
		btn_layout = QHBoxLayout(btn_widget)
		
		self.buttons = {}
		for (key, name, slot) in (
	 	    ("convert","&Convert", self.onConvert),
	    	("report", "&Report", self.onReport),
	    	("quit", "&Quit", self.onQuit)
	    	):
			btn = QPushButton(name)
			if (key != "quit"):
				btn.setDisabled(True)
			btn.clicked.connect(slot)

			btn_layout.addWidget(btn)

			self.buttons[key] = btn

		# Layouts
		centralLayout = QVBoxLayout(centralWgt)
		centralLayout.addWidget(pathbox)
		centralLayout.addWidget(tbox)
		centralLayout.addWidget(btn_widget, 2)
		
		self._center()

	def _center(self):
		frameGm = self.frameGeometry()
		screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
		centerPoint = QApplication.desktop().screenGeometry(screen).center()
		frameGm.moveCenter(centerPoint)
		self.move(frameGm.topLeft())

	def _updateStatus(self, status):
		# Clear statusbar
		for children in self.statusBar().children():
			if isinstance(children, QWidget):
				self.statusBar().removeWidget(children)

		# Size image
		text = '{} x {}'.format(*status)
		infobar = QWidget()
		layout =  QFormLayout(infobar)	
		layout.addRow("size:", QLabel(text))		
		self.statusBar().addWidget(infobar, 2)

		# Progress is converting file
		self.progress = 0
		self.progressbar = QProgressBar()
		self.progressbar.setRange(0, status[0])
		self.progressbar.setValue(self.progress)
		self.statusBar().addWidget(self.progressbar)

	def closeEvent(self, event):
		self.onQuit()

	@QtCore.pyqtSlot()
	def doProgress(self):
		self.progress += 1
		self.progressbar.setValue(self.progress)

	def onOpenImage(self):
		answer = QFileDialog.getOpenFileName(self, 
										    "Open Image", 
											"",
										    "Image Files (*.png *.jpg *.bmp)")[0];
		if not answer:
			return
		
		self.paths['source'] = answer 
		self.paths['output'] = os.path.join(os.path.dirname(answer), 'output.txt') 

		for k,v in self.lines.items():
			v.setEnabled(True)
			v.setText(self.paths[k])
			v.setToolTip(self.paths[k])
			v.setCursorPosition(0)

		self.image = ImageHex(self.paths['source'], mode=self.image_mode)
		self.image.signal.progressed.connect(self.doProgress)
		
		self._updateStatus(self.image.get_size())
		
		self.buttons["convert"].setEnabled(True)

	def onSaveOutput(self):
		ans = QFileDialog.getSaveFileName(self, 
			"Save file", 
			"",
			"Text Files (*.txt)")[0]	
		if not ans:
			return
		
		self.paths['output'] = ans	
		self.lines['output'].setEnabled(True)
		self.lines['output'].setText(self.paths[''])
		self.lines['output'].setToolTip(self.paths[''])
		self.lines['output'].setCursorPosition(0)
		
	def onConvert(self):
		self.seq = self.image.compress()
		report(self.seq, self.paths['output'])
		self.buttons["report"].setEnabled(True)

	def onReport(self):
		if os.path.exists(self.paths['output']): 
			self.open_report()
		else:
			self.statusBar().showMessage("Error! Don't exist file", 1000)

	def open_report(self):
		if sys.platform == 'win32':
			cmd = "start"
		else:
			cmd = "xdg-open"	
		answer = os.system(" ".join([cmd, self.paths['output']])) 
		if (answer != 0):
			self.statusBar().showMessage("Error. Can't open output file")

	def onQuit(self):
		QtCore.QCoreApplication.exit(0)



if __name__ == "__main__":
	app = QApplication(sys.argv)

	image_app = ImageApp()
	image_app.show()
	sys.exit(app.exec_())




