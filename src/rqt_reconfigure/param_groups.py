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
        self._tab_bar = None  # Every group can have one tab bar

        self._verticalLayout = QVBoxLayout(self)
        self._verticalLayout.setContentsMargins(QMargins(0, 0, 0, 0))

        grid_widget = QWidget(self)
        self._grid = QFormLayout(grid_widget)
        self.insert_widget_on_top(grid_widget)

        logging.debug('Groups node name={}'.format(node_name))

    def insert_widget_on_top(self, widget):
        self._verticalLayout.insertWidget(0, widget)

    def add_editor_widget(self, parameter, depth=0):
        tokens = parameter.name.split('.', depth + 1)
        if len(tokens) == depth + 1:
            descriptor = self._param_client.describe_parameters(
                             [parameter.name])[0]
            if descriptor.additional_constraints == '':
                if Parameter.Type(descriptor.type) not in EDITOR_TYPES:
                    return
                editor_widget = EDITOR_TYPES[Parameter.Type(descriptor.type)](
                                    self._param_client, parameter, descriptor)
            else:
                editor_widget = EnumEditor(self._param_client,
                                           parameter, descriptor)
            print('*** add editor: ' + parameter.name)
            logging.debug('Adding editor widget for {}'.format(parameter.name))
            editor_widget.display(self._grid)
            self._editor_widgets[parameter.name] = editor_widget
        else:
            group_name = tokens[depth]
            group = self._group_widgets.get(group_name, None)
            if group is None:
                if self._tab_bar is None:
                    print('*** add tab_bar')
                    self._tab_bar = QTabWidget()
                    #self._tab_bar.tabBar().installEventFilter(self)
                    self._grid.addRow(self._tab_bar)
                print('*** add group: ' + group_name)
                group = GroupWidget(self._param_client, group_name)
                self._group_widgets[group_name] = group
            group.add_editor_widget(parameter, depth + 1)

    def remove_editor_widget(self, parameter, depth=0):
        tokens = parameter.name.split('.', depth + 1)
        if len(tokens) == depth + 1:
            if parameter.name in self._editor_widgets:
                logging.debug('Removing editor widget for {}'.format(parameter.name))
                self._editor_widgets[parameter.name].hide(self._grid)
                self._editor_widgets[parameter.name].close()
                del self._editor_widgets[parameter.name]
        else:
            group_name = tokens[depth]
            group = self._group_widgets.get(group_name, None)
            if group is not None and \
               group.remove_editor_widget(parameter, depth + 1) == 0:
                del self._group_widgets[group_name]
        return len(self._editor_widgets)

    def update_editor_widget(self, parameter, depth=0):
        tokens = parameter.name.split('.', depth + 1)
        if len(tokens) == depth + 1:
            if parameter.name in self._editor_widgets:
                logging.debug('Updating editor widget for {}'.format(parameter.name))
                self._editor_widgets[parameter.name].update_local(parameter.value)
        else:
            group_name = tokens[depth]
            group = self._group_widgets.get(group_name, None)
            if group is not None:
                group.update_editor_widget(parameter, depth + 1)

    def close(self):
        for editor_widget in self._editor_widgets.values():
            editor_widget.close()
        for group_widget in self._group_widgets.values():
            group_widget.close()

    def _node_disable_bt_clicked(self):
        logging.debug('param_gs _node_disable_bt_clicked')
        self.sig_node_disabled_selected.emit(self._toplevel_treenode_name)


class TabGroup(GroupWidget):
    def __init__(self, parent, param_client, group_name):
        super(TabGroup, self).__init__(param_client, group_name)
        self._parent = parent

        # if not self._parent.tab_bar:
        #     self._parent.tab_bar = QTabWidget()

        #     # Don't process wheel events when not focused
        #     self._parent.tab_bar.tabBar().installEventFilter(self)

        #self._parent.tab_bar.addTab(self, group_name)

    def close(self):
        super(TabGroup, self).close()
        self._parent.tab_bar = None
        self._parent.tab_bar_shown = False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and not obj.hasFocus():
            return True
        return super(GroupWidget, self).eventFilter(obj, event)
