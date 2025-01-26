# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'about.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget)
from . import main_rc

class Ui_DialogAbout(object):
    def setupUi(self, DialogAbout):
        if not DialogAbout.objectName():
            DialogAbout.setObjectName(u"DialogAbout")
        DialogAbout.setWindowModality(Qt.WindowModality.ApplicationModal)
        DialogAbout.resize(561, 584)
        DialogAbout.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        icon = QIcon()
        icon.addFile(u":/window/icon_48x48.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        DialogAbout.setWindowIcon(icon)
        DialogAbout.setModal(True)
        self.verticalLayout = QVBoxLayout(DialogAbout)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self._frm_info = QFrame(DialogAbout)
        self._frm_info.setObjectName(u"_frm_info")
        self._frm_info.setFrameShape(QFrame.Shape.NoFrame)
        self._frm_info.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self._frm_info)
        self.horizontalLayout_6.setSpacing(9)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self._l_infor_icon = QLabel(self._frm_info)
        self._l_infor_icon.setObjectName(u"_l_infor_icon")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self._l_infor_icon.sizePolicy().hasHeightForWidth())
        self._l_infor_icon.setSizePolicy(sizePolicy)
        self._l_infor_icon.setMinimumSize(QSize(128, 128))
        self._l_infor_icon.setPixmap(QPixmap(u":/window/logo_128x128.png"))
        self._l_infor_icon.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.horizontalLayout_6.addWidget(self._l_infor_icon)

        self._l_info_text = QLabel(self._frm_info)
        self._l_info_text.setObjectName(u"_l_info_text")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self._l_info_text.sizePolicy().hasHeightForWidth())
        self._l_info_text.setSizePolicy(sizePolicy1)
        self._l_info_text.setWordWrap(True)

        self.horizontalLayout_6.addWidget(self._l_info_text)


        self.verticalLayout.addWidget(self._frm_info)

        self._frm_app_version = QFrame(DialogAbout)
        self._frm_app_version.setObjectName(u"_frm_app_version")
        self._frm_app_version.setFrameShape(QFrame.Shape.NoFrame)
        self._frm_app_version.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self._frm_app_version)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self._l_app_name = QLabel(self._frm_app_version)
        self._l_app_name.setObjectName(u"_l_app_name")
        sizePolicy.setHeightForWidth(self._l_app_name.sizePolicy().hasHeightForWidth())
        self._l_app_name.setSizePolicy(sizePolicy)

        self.horizontalLayout_5.addWidget(self._l_app_name)

        self.l_app_version = QLabel(self._frm_app_version)
        self.l_app_version.setObjectName(u"l_app_version")

        self.horizontalLayout_5.addWidget(self.l_app_version)

        self.btn_updates = QPushButton(self._frm_app_version)
        self.btn_updates.setObjectName(u"btn_updates")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.btn_updates.sizePolicy().hasHeightForWidth())
        self.btn_updates.setSizePolicy(sizePolicy2)

        self.horizontalLayout_5.addWidget(self.btn_updates)


        self.verticalLayout.addWidget(self._frm_app_version)

        self._frm_updates_status = QFrame(DialogAbout)
        self._frm_updates_status.setObjectName(u"_frm_updates_status")
        self._frm_updates_status.setFrameShape(QFrame.Shape.StyledPanel)
        self._frm_updates_status.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self._frm_updates_status)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.l_updates_status = QLabel(self._frm_updates_status)
        self.l_updates_status.setObjectName(u"l_updates_status")

        self.horizontalLayout_2.addWidget(self.l_updates_status)


        self.verticalLayout.addWidget(self._frm_updates_status)

        self._frm_dev_version = QFrame(DialogAbout)
        self._frm_dev_version.setObjectName(u"_frm_dev_version")
        self._frm_dev_version.setFrameShape(QFrame.Shape.NoFrame)
        self._frm_dev_version.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self._frm_dev_version)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self._l_dev_name = QLabel(self._frm_dev_version)
        self._l_dev_name.setObjectName(u"_l_dev_name")
        sizePolicy.setHeightForWidth(self._l_dev_name.sizePolicy().hasHeightForWidth())
        self._l_dev_name.setSizePolicy(sizePolicy)

        self.horizontalLayout_4.addWidget(self._l_dev_name)

        self.l_dev_version = QLabel(self._frm_dev_version)
        self.l_dev_version.setObjectName(u"l_dev_version")

        self.horizontalLayout_4.addWidget(self.l_dev_version)


        self.verticalLayout.addWidget(self._frm_dev_version)

        self._frm_runtime_info = QFrame(DialogAbout)
        self._frm_runtime_info.setObjectName(u"_frm_runtime_info")
        self._frm_runtime_info.setFrameShape(QFrame.Shape.NoFrame)
        self._frm_runtime_info.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self._frm_runtime_info)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self._frm_runtime_info_1 = QFrame(self._frm_runtime_info)
        self._frm_runtime_info_1.setObjectName(u"_frm_runtime_info_1")
        self._frm_runtime_info_1.setFrameShape(QFrame.Shape.StyledPanel)
        self._frm_runtime_info_1.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self._frm_runtime_info_1)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self._l_runtime_title = QLabel(self._frm_runtime_info_1)
        self._l_runtime_title.setObjectName(u"_l_runtime_title")

        self.horizontalLayout.addWidget(self._l_runtime_title)

        self.btn_copy_runtime_info = QPushButton(self._frm_runtime_info_1)
        self.btn_copy_runtime_info.setObjectName(u"btn_copy_runtime_info")
        sizePolicy2.setHeightForWidth(self.btn_copy_runtime_info.sizePolicy().hasHeightForWidth())
        self.btn_copy_runtime_info.setSizePolicy(sizePolicy2)
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditCopy))
        self.btn_copy_runtime_info.setIcon(icon1)

        self.horizontalLayout.addWidget(self.btn_copy_runtime_info)


        self.verticalLayout_2.addWidget(self._frm_runtime_info_1)

        self.txt_runtime_info = QTextEdit(self._frm_runtime_info)
        self.txt_runtime_info.setObjectName(u"txt_runtime_info")
        self.txt_runtime_info.setFrameShape(QFrame.Shape.Panel)
        self.txt_runtime_info.setFrameShadow(QFrame.Shadow.Sunken)
        self.txt_runtime_info.setReadOnly(True)

        self.verticalLayout_2.addWidget(self.txt_runtime_info)


        self.verticalLayout.addWidget(self._frm_runtime_info)


        self.retranslateUi(DialogAbout)

        QMetaObject.connectSlotsByName(DialogAbout)
    # setupUi

    def retranslateUi(self, DialogAbout):
        DialogAbout.setWindowTitle(QCoreApplication.translate("DialogAbout", u"About NanoVNASaver", None))
        self._l_infor_icon.setText("")
        self._l_info_text.setText(QCoreApplication.translate("DialogAbout", u"<html><head/><body><p>NanoVNASaver</p><p>\u00a9 Copyright 2019, 2020 Rune B. Broberg</p><p>\u00a9 Copyright 2020ff NanoVNA-Saver Authors</p><p>This program comes with ABSOLUTELY NO WARRANTY</p><p>This program is licensed under the GNU General Public License version 3</p><p>For further details, see: <a href=\"https://github.com/NanoVNA-Saver/nanovna-saver\"><span style=\" text-decoration: underline; color:#444444;\">https://github.com/NanoVNA-Saver/nanovna-saver</span></a></p></body></html>", None))
        self._l_app_name.setText(QCoreApplication.translate("DialogAbout", u"NanoVNA Saver: ", None))
        self.l_app_version.setText(QCoreApplication.translate("DialogAbout", u"v1.2.3", None))
        self.btn_updates.setText(QCoreApplication.translate("DialogAbout", u"Check for updates", None))
        self.l_updates_status.setText("")
        self._l_dev_name.setText(QCoreApplication.translate("DialogAbout", u"NanoVNA Firmware: ", None))
        self.l_dev_version.setText(QCoreApplication.translate("DialogAbout", u"not connected.", None))
        self._l_runtime_title.setText(QCoreApplication.translate("DialogAbout", u"Runtime information", None))
        self.btn_copy_runtime_info.setText(QCoreApplication.translate("DialogAbout", u"Copy", None))
        self.txt_runtime_info.setDocumentTitle("")
        self.txt_runtime_info.setHtml(QCoreApplication.translate("DialogAbout", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">System: Win x64</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Python: 3.10</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">PySide: 123</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-r"
                        "ight:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
    # retranslateUi

