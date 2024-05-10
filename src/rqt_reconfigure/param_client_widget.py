# Copyright (c) 2019 Open Source Robotics Foundation, Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the copyright holder nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# Author: Gonzalo de Pedro

from python_qt_binding.QtCore import QMargins, QSize, Qt, Signal
from python_qt_binding.QtGui import QFont, QIcon
from python_qt_binding.QtWidgets import (QFileDialog, QHBoxLayout, QLabel,
                                         QPushButton, QWidget)

from rclpy.parameter import Parameter
from rqt_reconfigure import logging
from rqt_reconfigure.param_api import create_param_client

"""
 Editor classes that are not explicitly used within this .py file still need
 to be imported. They are invoked implicitly during runtime.
"""
from rqt_reconfigure.param_editors import (BooleanEditor,  # noqa: F401
                                           DoubleEditor, EDITOR_TYPES,
                                           EditorWidget, IntegerEditor,
                                           StringEditor, EnumEditor)
from rqt_reconfigure.text_filter import TextFilter
from rqt_reconfigure.text_filter_widget import TextFilterWidget
from rqt_reconfigure.param_groups import GroupWidget

import yaml


class ParamClientWidget(GroupWidget):
    # Represents a widget where users can view and modify ROS params.

    sig_node_disabled_selected = Signal(str)

    def __init__(self, context, node_name):
        """
        Initializaze things.

        :type node_name: str
        """
        super(ParamClientWidget, self).__init__(
            create_param_client(context.node, node_name,
                                self._handle_param_event), node_name)

        self._node_grn = node_name
        self._toplevel_treenode_name = node_name

        widget_nodeheader = QWidget()
        h_layout_nodeheader = QHBoxLayout(widget_nodeheader)
        h_layout_nodeheader.setContentsMargins(QMargins(0, 0, 0, 0))

        # Save and load buttons
        load_button = QPushButton()
        load_button.setIcon(QIcon.fromTheme('document-open'))
        load_button.setToolTip('Load parameters from file')
        load_button.clicked[bool].connect(self._handle_load_clicked)
        load_button.setFixedSize(QSize(36, 24))
        h_layout_nodeheader.addWidget(load_button)
        save_button = QPushButton()
        save_button.setIcon(QIcon.fromTheme('document-save'))
        save_button.setToolTip('Save parameters to file')
        save_button.clicked[bool].connect(self._handle_save_clicked)
        save_button.setFixedSize(QSize(36, 24))
        h_layout_nodeheader.addWidget(save_button)

        nodename_qlabel = QLabel(self)
        font = QFont('Trebuchet MS, Bold')
        font.setUnderline(True)
        font.setBold(True)
        font.setPointSize(10)
        nodename_qlabel.setFont(font)
        nodename_qlabel.setAlignment(Qt.AlignCenter)
        nodename_qlabel.setText(node_name)
        h_layout_nodeheader.addWidget(nodename_qlabel)

        # Button to close a node.
        bt_disable_node = QPushButton(self)
        bt_disable_node.setIcon(QIcon.fromTheme('window-close'))
        bt_disable_node.setToolTip('Hide this node')
        bt_disable_node_size = QSize(36, 24)
        bt_disable_node.setFixedSize(bt_disable_node_size)
        bt_disable_node.pressed.connect(self._node_disable_bt_clicked)
        h_layout_nodeheader.addWidget(bt_disable_node)

        # Parameter filter
        filter_widget = QWidget()
        filter_h_layout = QHBoxLayout(filter_widget)
        self._text_filter = TextFilter(self)
        text_filter_widget = TextFilterWidget(self._text_filter)
        filter_label = QLabel('&Filter param:')
        filter_label.setBuddy(text_filter_widget)
        filter_h_layout.addWidget(filter_label)
        filter_h_layout.addWidget(text_filter_widget)

        self.insert_widget_on_top(filter_widget)
        self.insert_widget_on_top(widget_nodeheader)

        # Again, these UI operation above needs to happen in .ui file.
        try:
            self.add_editor_widgets(self._param_client.get_parameters(
                                        self._param_client.list_parameters()))
        except Exception as e:
            logging.warn(
              f'Failed to retrieve parameters from node {self._node_grn}: {e}')

        self._text_filter.filter_changed_signal.connect(
            self._filter_key_changed)

        self.setMinimumWidth(150)

    def get_node_grn(self):
        return self._node_grn

    def _handle_param_event(self, new_parameters,
                            changed_parameters, deleted_parameters):
        # TODO: Think about replacing callback architecture with signals.
        if new_parameters:
            try:
                self.add_editor_widgets(new_parameters)
            except Exception as e:
                logging.warn(
                    'Failed to get information about parameters: ' + str(e))

        if changed_parameters:
            self.update_editor_widgets(changed_parameters)
        if deleted_parameters:
            self.remove_editor_widgets(deleted_parameters)

    def _handle_load_clicked(self):
        filename = QFileDialog.getOpenFileName(
            self, self.tr('Load from File'), '.',
            self.tr('YAML file {.yaml} (*.yaml)'))
        if filename[0] != '':
            self.load_param(filename[0])

    def _handle_save_clicked(self):
        filename = QFileDialog.getSaveFileName(
            self, self.tr('Save parameters to file...'), '.',
            self.tr('YAML files {.yaml} (*.yaml)'))
        if filename[0] != '':
            self.save_param(filename[0])

    def save_param(self, filename):
        with open(filename, 'w') as f:
            try:
                parameters = self._param_client.get_parameters(
                                 self._param_client.list_parameters())
                yaml.dump({p.name: p.value for p in parameters}, f)
            except Exception as e:
                logging.warn(
                    "Parameter saving wasn't successful because: " + str(e)
                )

    def load_param(self, filename):
        with open(filename, 'r') as f:
            parameters = [Parameter(name=name, value=value)
                          for doc in yaml.safe_load_all(f.read())
                          for name, value in doc.items()]
        try:
            self._param_client.set_parameters(parameters)
        except Exception as e:
            logging.warn(
                "Parameter loading wasn't successful"
                ' because: {}'.format(e)
            )

    def add_editor_widgets(self, parameters):
        for parameter in parameters:
            self.add_editor_widget(parameter)

    def remove_editor_widgets(self, parameters):
        for parameter in parameters:
            self.remove_editor_widget(parameter)

    def update_editor_widgets(self, parameters):
        for parameter in parameters:
            self.update_editor_widget(parameter)

    def get_treenode_names(self):
        return list(self._editor_widgets.keys())

    def close(self):
        super(ParamClientWidget, self).close()
        self._param_client.close()
        self.deleteLater()

    def _node_disable_bt_clicked(self):
        logging.debug('param_gs _node_disable_bt_clicked')
        self.sig_node_disabled_selected.emit(self._toplevel_treenode_name)

    def _filter_key_changed(self):
        self._filter_param(self._text_filter.get_text())

    def _filter_param(self, filter_key):
        try:
            param_names = self._param_client.list_parameters()
            self.remove_editor_widgets(
                self._param_client.get_parameters(param_names))

            param_names_filtered = \
                list(filter(lambda p: filter_key in p, param_names)) if filter_key else param_names
            self.add_editor_widgets(
                self._param_client.get_parameters(param_names_filtered))
        except Exception as e:
            logging.warn('Failed to retrieve parameters from node: ' + str(e))
