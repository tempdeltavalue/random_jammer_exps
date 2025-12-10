#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Frequency Hopping Spread Spectrum Lab
# Author: Solomon
# Copyright: Solomon
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import learning_fhss_epy_block_0 as epy_block_0  # embedded python block
import learning_fhss_epy_block_0_0 as epy_block_0_0  # embedded python block
import math
import sip
import threading
import time



class learning_fhss(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Frequency Hopping Spread Spectrum Lab", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Frequency Hopping Spread Spectrum Lab")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "learning_fhss")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.vol_lvl = vol_lvl = 0.001
        self.variable_function_probe_0_0 = variable_function_probe_0_0 = 0
        self.variable_function_probe_0 = variable_function_probe_0 = 0
        self.samp_rate = samp_rate = 4.8e6
        self.noise_lvl = noise_lvl = 0
        self.activate_txer_fhss = activate_txer_fhss = 0
        self.activate_rxer_fhss = activate_rxer_fhss = 0

        ##################################################
        # Blocks
        ##################################################

        self._vol_lvl_range = qtgui.Range(0, 0.005, 0.0001, 0.001, 200)
        self._vol_lvl_win = qtgui.RangeWidget(self._vol_lvl_range, self.set_vol_lvl, "Volume Lvl", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._vol_lvl_win)
        self.tab = Qt.QTabWidget()
        self.tab_widget_0 = Qt.QWidget()
        self.tab_layout_0 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tab_widget_0)
        self.tab_grid_layout_0 = Qt.QGridLayout()
        self.tab_layout_0.addLayout(self.tab_grid_layout_0)
        self.tab.addTab(self.tab_widget_0, 'TX and Channel')
        self.tab_widget_1 = Qt.QWidget()
        self.tab_layout_1 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tab_widget_1)
        self.tab_grid_layout_1 = Qt.QGridLayout()
        self.tab_layout_1.addLayout(self.tab_grid_layout_1)
        self.tab.addTab(self.tab_widget_1, 'RX')
        self.tab_widget_2 = Qt.QWidget()
        self.tab_layout_2 = Qt.QBoxLayout(Qt.QBoxLayout.TopToBottom, self.tab_widget_2)
        self.tab_grid_layout_2 = Qt.QGridLayout()
        self.tab_layout_2.addLayout(self.tab_grid_layout_2)
        self.tab.addTab(self.tab_widget_2, 'Audio')
        self.top_layout.addWidget(self.tab)
        self._noise_lvl_range = qtgui.Range(0, 0.1, 0.01, 0, 200)
        self._noise_lvl_win = qtgui.RangeWidget(self._noise_lvl_range, self.set_noise_lvl, "Noise Lvl", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._noise_lvl_win)
        self.epy_block_0_0 = epy_block_0_0.blk()
        self.epy_block_0 = epy_block_0.blk()
        # Create the options list
        self._activate_txer_fhss_options = [0, 1]
        # Create the labels list
        self._activate_txer_fhss_labels = ['Deactivate', 'Activate']
        # Create the combo box
        # Create the radio buttons
        self._activate_txer_fhss_group_box = Qt.QGroupBox("Activate TX FHSS" + ": ")
        self._activate_txer_fhss_box = Qt.QHBoxLayout()
        class variable_chooser_button_group(Qt.QButtonGroup):
            def __init__(self, parent=None):
                Qt.QButtonGroup.__init__(self, parent)
            @pyqtSlot(int)
            def updateButtonChecked(self, button_id):
                self.button(button_id).setChecked(True)
        self._activate_txer_fhss_button_group = variable_chooser_button_group()
        self._activate_txer_fhss_group_box.setLayout(self._activate_txer_fhss_box)
        for i, _label in enumerate(self._activate_txer_fhss_labels):
            radio_button = Qt.QRadioButton(_label)
            self._activate_txer_fhss_box.addWidget(radio_button)
            self._activate_txer_fhss_button_group.addButton(radio_button, i)
        self._activate_txer_fhss_callback = lambda i: Qt.QMetaObject.invokeMethod(self._activate_txer_fhss_button_group, "updateButtonChecked", Qt.Q_ARG("int", self._activate_txer_fhss_options.index(i)))
        self._activate_txer_fhss_callback(self.activate_txer_fhss)
        self._activate_txer_fhss_button_group.buttonClicked[int].connect(
            lambda i: self.set_activate_txer_fhss(self._activate_txer_fhss_options[i]))
        self.top_layout.addWidget(self._activate_txer_fhss_group_box)
        # Create the options list
        self._activate_rxer_fhss_options = [0, 1]
        # Create the labels list
        self._activate_rxer_fhss_labels = ['Deactivate', 'Activate']
        # Create the combo box
        # Create the radio buttons
        self._activate_rxer_fhss_group_box = Qt.QGroupBox("Activate RX FHSS" + ": ")
        self._activate_rxer_fhss_box = Qt.QHBoxLayout()
        class variable_chooser_button_group(Qt.QButtonGroup):
            def __init__(self, parent=None):
                Qt.QButtonGroup.__init__(self, parent)
            @pyqtSlot(int)
            def updateButtonChecked(self, button_id):
                self.button(button_id).setChecked(True)
        self._activate_rxer_fhss_button_group = variable_chooser_button_group()
        self._activate_rxer_fhss_group_box.setLayout(self._activate_rxer_fhss_box)
        for i, _label in enumerate(self._activate_rxer_fhss_labels):
            radio_button = Qt.QRadioButton(_label)
            self._activate_rxer_fhss_box.addWidget(radio_button)
            self._activate_rxer_fhss_button_group.addButton(radio_button, i)
        self._activate_rxer_fhss_callback = lambda i: Qt.QMetaObject.invokeMethod(self._activate_rxer_fhss_button_group, "updateButtonChecked", Qt.Q_ARG("int", self._activate_rxer_fhss_options.index(i)))
        self._activate_rxer_fhss_callback(self.activate_rxer_fhss)
        self._activate_rxer_fhss_button_group.buttonClicked[int].connect(
            lambda i: self.set_activate_rxer_fhss(self._activate_rxer_fhss_options[i]))
        self.top_layout.addWidget(self._activate_rxer_fhss_group_box)
        def _variable_function_probe_0_0_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.epy_block_0_0.change_channel(activate_rxer_fhss)
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_variable_function_probe_0_0,val))
              except AttributeError:
                self.set_variable_function_probe_0_0(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (1))
        _variable_function_probe_0_0_thread = threading.Thread(target=_variable_function_probe_0_0_probe)
        _variable_function_probe_0_0_thread.daemon = True
        _variable_function_probe_0_0_thread.start()
        def _variable_function_probe_0_probe():
          self.flowgraph_started.wait()
          while True:

            val = self.epy_block_0.change_channel(activate_txer_fhss)
            try:
              try:
                self.doc.add_next_tick_callback(functools.partial(self.set_variable_function_probe_0,val))
              except AttributeError:
                self.set_variable_function_probe_0(val)
            except AttributeError:
              pass
            time.sleep(1.0 / (1))
        _variable_function_probe_0_thread = threading.Thread(target=_variable_function_probe_0_probe)
        _variable_function_probe_0_thread.daemon = True
        _variable_function_probe_0_thread.start()
        self.rational_resampler_xxx_0 = filter.rational_resampler_fff(
                interpolation=100,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.qtgui_waterfall_sink_x_1_0 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "RX Signal before LPF", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_1_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_1_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_1_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_1_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_1_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_1_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_1_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_1_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_1_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_1_0.qwidget(), Qt.QWidget)

        self.tab_layout_1.addWidget(self._qtgui_waterfall_sink_x_1_0_win)
        self.qtgui_waterfall_sink_x_1 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "RX Signal after LPF", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_1.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_1.enable_grid(False)
        self.qtgui_waterfall_sink_x_1.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_1.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_1.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_1.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_1.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_1.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_1_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_1.qwidget(), Qt.QWidget)

        self.tab_layout_1.addWidget(self._qtgui_waterfall_sink_x_1_win)
        self.qtgui_waterfall_sink_x_0_0 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Channel", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_0_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0_0.qwidget(), Qt.QWidget)

        self.tab_layout_0.addWidget(self._qtgui_waterfall_sink_x_0_0_win)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "TX Signal", #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.tab_layout_0.addWidget(self._qtgui_waterfall_sink_x_0_win)
        self.qtgui_freq_sink_x_0 = qtgui.freq_sink_f(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "", #name
            1,
            None # parent
        )
        self.qtgui_freq_sink_x_0.set_update_time(0.01)
        self.qtgui_freq_sink_x_0.set_y_axis((-140), 10)
        self.qtgui_freq_sink_x_0.set_y_label('Relative Gain', 'dB')
        self.qtgui_freq_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.qtgui_freq_sink_x_0.enable_autoscale(False)
        self.qtgui_freq_sink_x_0.enable_grid(False)
        self.qtgui_freq_sink_x_0.set_fft_average(1.0)
        self.qtgui_freq_sink_x_0.enable_axis_labels(True)
        self.qtgui_freq_sink_x_0.enable_control_panel(False)
        self.qtgui_freq_sink_x_0.set_fft_window_normalized(False)


        self.qtgui_freq_sink_x_0.set_plot_pos_half(not True)

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_freq_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_freq_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_freq_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_freq_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_freq_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_freq_sink_x_0_win = sip.wrapinstance(self.qtgui_freq_sink_x_0.qwidget(), Qt.QWidget)
        self.tab_layout_2.addWidget(self._qtgui_freq_sink_x_0_win)
        self.freq_xlating_fir_filter_xxx_1 = filter.freq_xlating_fir_filter_ccc(1, [1], 0, samp_rate)
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(1, [1], 0, samp_rate)
        self.filter_fft_low_pass_filter_0_0 = filter.fft_filter_ccc(1, firdes.low_pass(1, samp_rate, 15e3, 3e3, window.WIN_HAMMING, 6.76), 1)
        self.filter_fft_low_pass_filter_0 = filter.fft_filter_ccc(1, firdes.low_pass(1, samp_rate, 15e3, 3e3, window.WIN_HAMMING, 6.76), 1)
        self.blocks_wavfile_source_0 = blocks.wavfile_source('/Users/tempdelta/Desktop/jammer_exp/Bach_C_minor_Passacaglia_Variation_2.wav', True)
        self.blocks_throttle_0 = blocks.throttle(gr.sizeof_gr_complex*1, samp_rate,True)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(vol_lvl)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.audio_sink_0 = audio.sink(48000, '', True)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, noise_lvl, 0)
        self.analog_nbfm_rx_0 = analog.nbfm_rx(
        	audio_rate=int(48e3),
        	quad_rate=int(48e5),
        	tau=(75e-6),
        	max_dev=5e3,
          )
        self.analog_frequency_modulator_fc_0 = analog.frequency_modulator_fc((2*math.pi*(5e3)/samp_rate))
        self.analog_agc_xx_0 = analog.agc_ff((1e-4), 0.1, 0.1, 65536)


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.epy_block_0, 'freq'), (self.freq_xlating_fir_filter_xxx_1, 'freq'))
        self.msg_connect((self.epy_block_0_0, 'freq'), (self.freq_xlating_fir_filter_xxx_0, 'freq'))
        self.connect((self.analog_agc_xx_0, 0), (self.audio_sink_0, 0))
        self.connect((self.analog_agc_xx_0, 0), (self.qtgui_freq_sink_x_0, 0))
        self.connect((self.analog_frequency_modulator_fc_0, 0), (self.freq_xlating_fir_filter_xxx_1, 0))
        self.connect((self.analog_nbfm_rx_0, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.analog_noise_source_x_0, 0), (self.filter_fft_low_pass_filter_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_throttle_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))
        self.connect((self.blocks_throttle_0, 0), (self.qtgui_waterfall_sink_x_0_0, 0))
        self.connect((self.blocks_wavfile_source_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.filter_fft_low_pass_filter_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.filter_fft_low_pass_filter_0_0, 0), (self.analog_nbfm_rx_0, 0))
        self.connect((self.filter_fft_low_pass_filter_0_0, 0), (self.qtgui_waterfall_sink_x_1, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.filter_fft_low_pass_filter_0_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.qtgui_waterfall_sink_x_1_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_1, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.analog_frequency_modulator_fc_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "learning_fhss")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_vol_lvl(self):
        return self.vol_lvl

    def set_vol_lvl(self, vol_lvl):
        self.vol_lvl = vol_lvl
        self.blocks_multiply_const_vxx_0.set_k(self.vol_lvl)

    def get_variable_function_probe_0_0(self):
        return self.variable_function_probe_0_0

    def set_variable_function_probe_0_0(self, variable_function_probe_0_0):
        self.variable_function_probe_0_0 = variable_function_probe_0_0

    def get_variable_function_probe_0(self):
        return self.variable_function_probe_0

    def set_variable_function_probe_0(self, variable_function_probe_0):
        self.variable_function_probe_0 = variable_function_probe_0

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.analog_frequency_modulator_fc_0.set_sensitivity((2*math.pi*(5e3)/self.samp_rate))
        self.blocks_throttle_0.set_sample_rate(self.samp_rate)
        self.blocks_throttle_0_0.set_sample_rate(self.samp_rate)
        self.blocks_throttle_0_1.set_sample_rate(self.samp_rate)
        self.filter_fft_low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, 15e3, 3e3, window.WIN_HAMMING, 6.76))
        self.filter_fft_low_pass_filter_0_0.set_taps(firdes.low_pass(1, self.samp_rate, 15e3, 3e3, window.WIN_HAMMING, 6.76))
        self.qtgui_freq_sink_x_0.set_frequency_range(0, self.samp_rate)
        self.qtgui_waterfall_sink_x_0.set_frequency_range(0, self.samp_rate)
        self.qtgui_waterfall_sink_x_0_0.set_frequency_range(0, self.samp_rate)
        self.qtgui_waterfall_sink_x_1.set_frequency_range(0, self.samp_rate)
        self.qtgui_waterfall_sink_x_1_0.set_frequency_range(0, self.samp_rate)

    def get_noise_lvl(self):
        return self.noise_lvl

    def set_noise_lvl(self, noise_lvl):
        self.noise_lvl = noise_lvl
        self.analog_noise_source_x_0.set_amplitude(self.noise_lvl)

    def get_activate_txer_fhss(self):
        return self.activate_txer_fhss

    def set_activate_txer_fhss(self, activate_txer_fhss):
        self.activate_txer_fhss = activate_txer_fhss
        self._activate_txer_fhss_callback(self.activate_txer_fhss)

    def get_activate_rxer_fhss(self):
        return self.activate_rxer_fhss

    def set_activate_rxer_fhss(self, activate_rxer_fhss):
        self.activate_rxer_fhss = activate_rxer_fhss
        self._activate_rxer_fhss_callback(self.activate_rxer_fhss)




def main(top_block_cls=learning_fhss, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
