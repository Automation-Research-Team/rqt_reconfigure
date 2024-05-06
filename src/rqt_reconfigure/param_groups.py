# Copyright (c) 2012, Willow Garage, Inc.
# All rights reserved.
#
# Software License Agreement (BSD License 2.0)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Isaac Saito, Ze'ev Klapow

import time

from python_qt_binding.QtCore import (QEvent, QMargins, QObject, QSize, Qt,
                                      Signal)
from python_qt_binding.QtGui import QFont, QIcon
from python_qt_binding.QtWidgets import (QFormLayout, QGroupBox,
                                         QHBoxLayout, QLabel, QPushButton,
                                         QTabWidget, QVBoxLayout, QWidget)

from rclpy.parameter import Parameter
from rqt_reconfigure import logging
# *Editor classes that are not explicitly used within this .py file still need
# to be imported. They are invoked implicitly during runtime.
from rqt_reconfigure.param_editors import (  # noqa: F401
    BooleanEditor, DoubleEditor, EDITOR_TYPES, EditorWidget, EnumEditor,
    IntegerEditor, StringEditor
)


class GroupWidget(QWidget):
    """
    (Isaac's guess as of 12/13/2012)
    This class bonds multiple Editor instances that are associated with
    a single node as a group.
    """

    # public signal
    sig_node_disabled_selected = Signal(str)
    sig_node_state_change = Signal(bool)

    def __init__(self, param_client, node_name):
        """
        :param context:
        :type node_name: str
        """
        super(GroupWidget, self).__init__()
        self._param_client = param_client
        self._node_grn = node_name
        self._toplevel_treenode_name = node_name

        self._editor_widgets = {}
        self._group_widgets = {}
        self._param_names = []

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(QMargins(0, 0, 0, 0))

        self.grid_widget = QWidget(self)
        self.grid = QFormLayout(self.grid_widget)
        self.verticalLayout.addWidget(self.grid_widget, 1)

        self.tab_bar = None  # Every group can have one tab bar
        self.tab_bar_shown = False

        logging.debug('Groups node name={}'.format(node_name))

        # Labels should not stretch
        # self.grid.setColumnStretch(1, 1)
        # self.setLayout(self.grid)

    def collect_paramnames(self, config):
        pass

    def add_editor_widget(self, parameter, descriptor, depth):
        tokens = parameter.name.split('.', depth + 1)
        if len(tokens) == depth + 1:
            if descriptor.additional_constraints == '':
                if Parameter.Type(descriptor.type) not in EDITOR_TYPES:
                    return
                editor_widget = EDITOR_TYPES[Parameter.Type(descriptor.type)](
                                    self._param_client, parameter, descriptor)
            else:
                editor_widget = EnumEditor(self._param_client,
                                           parameter, descriptor)
            logging.debug('Adding editor widget for {}'.format(parameter.name))
            self.grid.addRow(editor_widget)
            self._editor_widgets[parameter.name] = editor_widget
        else:
            group_name = tokens[depth]
            if group_name not in self._group_widgets:
                group = TabGroup(self, self._param_client, group_name)
                group.display(self.grid)
                self._group_widgets[group_name] = group
            self._group_widgets[group_name].add_editor_widget(parameter,
                                                              descriptor,
                                                              depth + 1)

    def remove_editor_widget(self, parameter):
        if parameter.name not in self._editor_widgets:
            return
        logging.debug('Removing editor widget for {}'.format(parameter.name))
        self._editor_widgets[parameter.name].hide(self.grid)
        self._editor_widgets[parameter.name].close()
        del self._editor_widgets[parameter.name]

    def update_editor_widget(self, parameter):
        if parameter.name not in self._editor_widgets:
            return
        logging.debug('Updating editor widget for {}'.format(parameter.name))
        self._editor_widgets[parameter.name].update_local(parameter.value)

    def display(self, grid):
        grid.addRow(self)

    def close(self):
        for w in self._editor_widgets:
            w.close()

    def get_treenode_names(self):
        """
        :rtype: str[]
        """
        return self._param_names

    def _node_disable_bt_clicked(self):
        logging.debug('param_gs _node_disable_bt_clicked')
        self.sig_node_disabled_selected.emit(self._toplevel_treenode_name)


class TabGroup(GroupWidget):
    def __init__(self, parent, param_client, group_name):
        super(TabGroup, self).__init__(param_client, group_name)
        self._parent = parent

        if not self._parent.tab_bar:
            self._parent.tab_bar = QTabWidget()

            # Don't process wheel events when not focused
            self._parent.tab_bar.tabBar().installEventFilter(self)

        widget = QWidget()
        widget.setLayout(self.grid)
        parent.tab_bar.addTab(widget, group_name)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and not obj.hasFocus():
            return True
        return super(GroupWidget, self).eventFilter(obj, event)

    def display(self, grid):
        if not self._parent.tab_bar_shown:
            grid.addRow(self._parent.tab_bar)
            self._parent.tab_bar_shown = True

    def close(self):
        super(TabGroup, self).close()
        self._parent.tab_bar = None
        self._parent.tab_bar_shown = False
