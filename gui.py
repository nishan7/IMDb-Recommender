import sys
from PyQt5.QtGui import QFont

from PyQt5 import QtWidgets, QtCore, QtGui, Qt
from PyQt5.QtWidgets import (QLabel, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSpacerItem, QApplication,
                             QLineEdit, QScrollArea, QPushButton, QSizePolicy, QRadioButton, QButtonGroup)
import urllib
import webbrowser
from recsys import get_recoms, imdb
from rapidfuzz import process
from difflib import SequenceMatcher
from heapq import nlargest as _nlargest
from flowlayout import FlowLayout

# Set a search mode, fuzzy is more precise and guesses better and difflib is much faster
SEARCH_MODE = 'fuzzy'


# SEARCH_MODE = 'difflib'


def get_best_matches(word, possibilities, n=5, cutoff=0.5):
    if SEARCH_MODE == 'difflib':
        """Use SequenceMatcher to return a list of the indexes of the best
        "good enough" matches. word is a sequence for which close matches
        are desired (typically a string).
        possibilities is a list of sequences against which to match word
        (typically a list of strings).
        Optional arg n (default 3) is the maximum number of close matches to
        return.  n must be > 0.
        Optional arg cutoff (default 0.6) is a float in [0, 1].  Possibilities
        that don't score at least that similar to word are ignored.
        """
        if not n > 0:
            raise ValueError("n must be > 0: %r" % (n,))
        if not 0.0 <= cutoff <= 1.0:
            raise ValueError("cutoff must be in [0.0, 1.0]: %r" % (cutoff,))
        result = []
        s = SequenceMatcher()
        s.set_seq2(word)
        for idx, x in enumerate(possibilities):
            s.set_seq1(x)
            if s.real_quick_ratio() >= cutoff and \
                    s.quick_ratio() >= cutoff and \
                    s.ratio() >= cutoff:
                result.append((s.ratio(), idx))

        # Move the best scorers to head of list
        result = _nlargest(n, result)

        # Strip scores for the best n matches
        return [x for score, x in result]
    elif SEARCH_MODE == 'fuzzy':
        matches = process.extractBests(word, possibilities, limit=5, score_cutoff=0.5)
        return [id for name, score, id in matches]


# It keeps track of all the titles which are selected and mement to be sent to the recomm system.
selected_titles_list = []


class SelectedTitleButton(QPushButton):
    # Creating a custem Label that allow to to be clicked and remove itself when clicked
    def __init__(self, text, id):
        QPushButton.__init__(self, "{} ❌".format(text))
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        self.setFlat(True)
        selected_titles_list.append(id)
        self.title_id = id

    def mousePressEvent(self, event):
        # print('Removed')
        self.setParent(None)
        selected_titles_list.remove(self.title_id)

    def enterEvent(self, QEvent):
        self.setStyleSheet("border:2px solid #ff3d38;")
        self.setFlat(False)

    def leaveEvent(self, QEvent):
        self.setFlat(True)
        self.setStyleSheet('')


class ClickableLabel(QLabel):
    # Creating a cutom label class that allows us click it, for the options as searched string

    clicked = QtCore.pyqtSignal()

    def __init__(self, text='', font_size=13, bold=False, background=True, underline=True):
        QLabel.__init__(self, text=text)
        self.link = "http://www.example.com"
        # self.text = text
        self.title_id= 0
        self.setContentsMargins(10, 5, 5, 5)

        # Storage data
        self.background = background
        self.font_size = font_size
        self.underline = underline
        self.bold = bold

        ##
        f = QFont()
        f.setPixelSize(self.font_size)
        f.setUnderline(self.underline)
        f.setBold(self.bold)
        self.setFont(f)
        f.setBold(self.bold)

        self.style_sheet = ''
        if background:
            self.style_sheet += 'background-color:#e1e1e8;'
        if underline:
            self.style_sheet += 'text:underline;'

        self.setStyleSheet(self.style_sheet)

    def mousePressEvent(self, event):
        # print(self.text)
        self.clicked.emit()
        QLabel.mousePressEvent(self, event)

    def enterEvent(self, QEvent):
        f = QFont()
        f.setPixelSize(15)
        f.setUnderline(True)
        f.setBold(True)
        self.setFont(f)

    def leaveEvent(self, QEvent):
        # here the code for mouse leave
        f = QFont()
        f.setPixelSize(self.font_size)
        f.setUnderline(self.underline)
        f.setBold(self.bold)
        self.setFont(f)


class ThreadedSearcher(QtCore.QThread):
    # This Threaded Class is used to search for the possible title for search string
    search_result_signal = QtCore.pyqtSignal(list)
    RUNNING = False

    def __init__(self):
        super().__init__()
        self.query = None

    def put_query(self, query):
        self.query = query
        # print(self.query)
        if not self.RUNNING:
            # print(self.stack)
            self.start()

    def run(self):
        self.RUNNING = True
        while self.query:
            matches = get_best_matches(self.query, imdb['title'])
            results = [(id, imdb['title'].iloc[id]) for id in matches]
            self.search_result_signal.emit(results)
            self.query = ''
        #     self.end_signal.emit(0)

        self.RUNNING = False

        return


class Recommendations(QtCore.QThread):
    # Threaded Class used get recommendations
    recom_signal = QtCore.pyqtSignal(list)

    def request(self, ids, mode):
        self.ids = ids
        self.mode = mode #Series or movies
        self.start()

    def run(self):
        recoms = get_recoms(self.ids,self.mode)
        self.recom_signal.emit(recoms)


class App(QMainWindow):
    PATH = None

    def __init__(self):
        super().__init__()
        self.window_title = 'Recommendations'
        self.left = 300
        self.top = 200
        self.width = 700
        self.height = 800

        self.searcher = ThreadedSearcher()
        self.searcher.search_result_signal.connect(self.recevice_search_options)
        self.searcher.start()

        self.recommender = Recommendations()
        self.recommender.recom_signal.connect(self.receive_recoms)

        self.initUI()

    def initUI(self):
        self.setWindowIcon(QtGui.QIcon('logo.png'))
        self.setWindowTitle(self.window_title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Topmost widget in the program
        self.mainWigdet = QWidget()
        # self.mainWigdet.setSizePolicy(QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.mainWigdet.setObjectName('main Widget')

        # Gets the toolbar layout from the function
        # self.toolbar = self.addToolbar()

        # Layout for search box and radio buttons
        self.searchArea = QHBoxLayout()

        self.search = QLineEdit()

        self.searchArea.addWidget(QLabel(text='Search'))
        self.searchArea.addWidget(self.search)

        self.recom_movies = QRadioButton('Movies')
        self.recom_series = QRadioButton('Series')

        self.recom_movies.setChecked(True)
        self.recom_movies_or_series  = QButtonGroup()
        self.recom_movies_or_series.setExclusive(True)


        self.recom_movies_or_series.addButton(self.recom_movies)
        self.recom_movies_or_series.addButton(self.recom_series)

        # self.searchArea.addItem(self.recom_movies_or_series)
        self.searchArea.addWidget(self.recom_movies)
        self.searchArea.addWidget(self.recom_series)

        self.search_button = QPushButton('Recommend!')
        self.searchArea.addWidget(self.search_button)

        # Layout for option/tooltip Area
        self.optionWidget = QWidget()

        self.tooltipAreaLayout = QVBoxLayout()
        self.tooltipAreaLayout.setAlignment(QtCore.Qt.AlignTop)

        option_value1 = ClickableLabel(text='1', background=True, underline=False)
        option_value2 = ClickableLabel(text='2', background=True, underline=False)
        option_value3 = ClickableLabel(text='3', background=True, underline=False)
        option_value4 = ClickableLabel(text='4', background=True, underline=False)
        option_value5 = ClickableLabel(text='5', background=True, underline=False)

        self.tooltipAreaLayout.addWidget(option_value1)
        self.tooltipAreaLayout.addWidget(option_value2)
        self.tooltipAreaLayout.addWidget(option_value3)
        self.tooltipAreaLayout.addWidget(option_value4)
        self.tooltipAreaLayout.addWidget(option_value5)

        self.optionWidget.setLayout(self.tooltipAreaLayout)

        #
        self.selected_options_layout = FlowLayout()

        #
        self.nameLabel = QLabel('Search for something')
        self.nameLabel.setFont(QFont("MS", pointSize=13, weight=QFont.Bold))
        self.nameLabel.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter)

        # Layout for contents Area
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.episodesContents = QWidget()

        self.episodesLayout = QVBoxLayout(self.episodesContents)

        # self.episodesLayout.addLayout(self.seasonBox('Season 1', 'Episdoes 5'))
        # self.episodesLayout.addLayout(self.seasonBox('Season 2', 'Episodes 3'))
        self.episodesLayout.addItem(
            QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        self.episodesContents.setLayout(self.episodesLayout)
        self.scrollArea.setWidget(self.episodesContents)

        # Finally setting of the application
        self.mainLayout = QVBoxLayout()
        # self.mainLayout.addLayout(self.toolbar)
        self.mainLayout.addLayout(self.searchArea)
        self.mainLayout.addWidget(self.optionWidget)
        self.mainLayout.addLayout(self.selected_options_layout)
        self.mainLayout.addWidget(self.nameLabel)

        self.mainLayout.addWidget(self.scrollArea)
        # self.mainLayout.addItem(QSpacerItem(20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

        self.mainWigdet.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWigdet)

        for i in self.optionWidget.children()[1:]:
            i.hide()

        # Setting up the status bar
        self.status = QtWidgets.QStatusBar()
        # self.status.showMessage()
        self.setStatusBar(self.status)

        # Events
        self.search.textChanged.connect(self.searched)
        self.search.returnPressed.connect(self.ask_for_recoms)
        self.search_button.clicked.connect(self.ask_for_recoms)

        option_value1.clicked.connect(self.optionClicked)
        option_value2.clicked.connect(self.optionClicked)
        option_value3.clicked.connect(self.optionClicked)
        option_value4.clicked.connect(self.optionClicked)
        option_value5.clicked.connect(self.optionClicked)



    def searched(self):  # When something is typed in search bar
        # print(self.search.text())
        if self.search.text() == '':
            for c in self.optionWidget.children()[1:]:
                c.hide()
        else:
            self.searcher.put_query(self.search.text())

    @QtCore.pyqtSlot(list)
    def recevice_search_options(self, results):
        # It receives the search option and puts it in option box
        i = 0
        # print(results)

        for i in range(5):  # Clears/hides all the clikable labels
            self.optionWidget.children()[i + 1].hide()

        if len(results) == 0:
            return

        for i in range(1, len(results) + 1):  # Creates new clickable labels
            self.optionWidget.children()[i].setText(results[i - 1][1])
            self.optionWidget.children()[i].show()
            self.optionWidget.children()[i].title_id=results[i-1][0]

            # self.optionWidget.children()[i].clicked.connect(self.optionClicked)
            # self.optionWidget.children()[i].mousePressEvent = lambda x: self.optionClicked(x, self.optionWidget.children()[i])

    def optionClicked(self):  # if any clickable label is clicked
        title = self.sender().text()
        id = self.sender().title_id
        # print(title,id)

        if id not in selected_titles_list:
            self.selected_options_layout.addWidget(SelectedTitleButton(text=title, id=id))

    def ask_for_recoms(self):
        print(selected_titles_list)
        if self.recom_movies.isChecked():
            self.recommender.request(selected_titles_list, 'movie')
        else:
            self.recommender.request(selected_titles_list, 'series')

        print([imdb['title'].iloc[id] for id in selected_titles_list])
        pass

    @QtCore.pyqtSlot(list)
    def receive_recoms(self, recoms):
        # print(recoms)
        self.show_recoms([' Recommendations ', recoms])

    def show_recoms(self, results):
        # It show the recomms in th UI
        name = results[0]
        # for c in self.episodesContents.children()[1:]:
        #     c.deleteLater()
        self.episodesContents.setParent(None)

        self.episodesContents = QWidget()

        self.episodesLayout = QVBoxLayout(self.episodesContents)
        self.nameLabel.setText(name)

        for title, imdb_id in results[1]:
            self.episodesLayout.addLayout(self.result_box(title, imdb_id))

        self.episodesLayout.addItem(
            QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        self.episodesContents.setLayout(self.episodesLayout)
        self.scrollArea.setWidget(self.episodesContents)

    def result_box(self, title, imdb_id):
        # It create a box inside which single recommendations is kept
        wrapper = QVBoxLayout()
        row = QHBoxLayout()

        seasonInfoColumn = QVBoxLayout()

        titlelabel = ClickableLabel('{}'.format(title), font_size=15, bold=True, underline=False, background=False)
        imdb_label = ClickableLabel('IMDb Id: {}'.format(imdb_id), font_size=14, bold=False, underline=False,
                                    background=False)

        titlelabel.setToolTip('Search {} in Google'.format(title))
        imdb_label.setToolTip('Search {} in IMDb'.format(title))

        seasonInfoColumn.addWidget(titlelabel)
        seasonInfoColumn.addWidget(imdb_label)

        row.addLayout(seasonInfoColumn)
        spacer = QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        row.addItem(spacer)
        result_search_btn = QPushButton('Search')
        result_search_btn.setToolTip('Search {} in Google'.format(title))
        # result_search_btn.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        result_search_btn.setMinimumSize(150, 65)
        row.addWidget(result_search_btn)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        wrapper.addItem(QSpacerItem(20, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        wrapper.addLayout(row)
        wrapper.addWidget(line)
        wrapper.addItem(QSpacerItem(20, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

        # rowWidget.setLayout(row)
        # Events
        result_search_btn.clicked.connect(
            lambda x: self.search_in_web('https://google.com/search?q=' + urllib.parse.quote(title)))
        titlelabel.mousePressEvent = lambda x: self.search_in_web(
            'https://google.com/search?q=' + urllib.parse.quote(title))
        imdb_label.mousePressEvent = lambda x: self.search_in_web('https://www.imdb.com/title/' + imdb_id)

        return wrapper

    def search_in_web(self, link):
        # webbrowser.open('https://google.com/search?q=' + urllib.parse.quote(self.data[id]['title']))
        webbrowser.open(link)

    # When some tv/movie  recmmenaation result is clicked
    def result_search_clicked(self, event, title, imdb_id):
        print(title, imdb_id)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    # time.sleep(5)
    a = app.exec_()
    print('After Closing')
    # endCleanup()
    sys.exit(a)
