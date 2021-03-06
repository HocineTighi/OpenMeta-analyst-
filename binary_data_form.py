##################################################
#
#  Byron C. Wallace
#  Tufts Medical Center
#  OpenMeta[analyst]
#  ---
#  Binary data form module; for flexible entry of dichotomous
#  outcome data
##################################################


from PyQt4.Qt import *
from PyQt4 import QtGui
import meta_py_r

import ui_binary_data_form
from ui_binary_data_form import Ui_BinaryDataForm

# @TODO this should be an *application global*. It is now a
# global here and in the data_table_view class. (However
# here we show four digits; there it is 3. We want different
# levels of granularity).
NUM_DIGITS = 4 

class BinaryDataForm2(QDialog, ui_binary_data_form.Ui_BinaryDataForm):
    
    def __init__(self, ma_unit, cur_txs, cur_effect, parent=None):
        super(BinaryDataForm2, self).__init__(parent)
        self.setupUi(self)
        self._setup_signals_and_slots()
        self.ma_unit = ma_unit
        self.raw_data = self.ma_unit.get_raw_data_for_groups(cur_txs)
        self.cur_groups = cur_txs
        self.cur_effect = cur_effect
        self._update_raw_data()
        self._update_data_table()
        self._populate_effect_data()
    
    def _setup_signals_and_slots(self):
        QObject.connect(self.raw_data_table, SIGNAL("cellChanged (int, int)"), 
                                                                                self._cell_changed)
        QObject.connect(self.effect_cbo_box, SIGNAL("currentIndexChanged(QString)"),
                                                                                self.effect_changed)                                                            
                                                                                 
    def _populate_effect_data(self):
        q_effects = sorted([QString(effect_str) for effect_str in self.ma_unit.effects_dict.keys()])
        self.effect_cbo_box.addItems(q_effects)
        self.effect_cbo_box.setCurrentIndex(q_effects.index(QString(self.cur_effect)))
        # populate fields with current effect data
        self.set_current_effect()

    def set_current_effect(self):
        effect_dict = self.ma_unit.effects_dict[self.cur_effect]
        for s, txt_box in zip(['est', 'lower', 'upper'], [self.effect_txt_box, self.low_txt_box, self.high_txt_box]):
            if effect_dict[s] is not None:
                txt_box.setText(QString("%s" % round(effect_dict[s], NUM_DIGITS)))
            else:
                txt_box.setText(QString(""))
        
    def effect_changed(self):
        self.cur_effect = unicode(self.effect_cbo_box.currentText().toUtf8(), "utf-8")
        self.set_current_effect()
        
    def _update_raw_data(self):
        ''' Generates the 2x2 table with whatever parametric data was provided '''
        self.raw_data_table.blockSignals(True)
        col = 0
        for i in range(4):
            item = QTableWidgetItem(str(self.raw_data[i]))
            row = 0 if i < 2 else 1
            col = i
            if row == 1:
                col = i - 2
            if col in (1,3):
                col += 1
            self.raw_data_table.setItem(row, col, item)
        self.raw_data_table.blockSignals(False)
        
    def _cell_changed(self, row, col):
        if row < 2:
            # the offset is for indexing the data
            # in the raw_data vector, which is one
            # dimensional (i.e., stretched 1X4) rather
            # than square (2x2)
            offset = 2 if row == 1 else 0
            if col in (0,2):
                # then raw data was changed.
                #
                # note that the 2x2 table is setup differently than the 
                # main data entry screen; the columns that correspond
                # to the raw data as entered in the main sheet and kept 
                # in MA units are 0 and 2 in the 2x2 table; namely,
                # the number of events and total N.
                adjusted_col = 1 if col==2 else 0
                index = offset + adjusted_col
                self.raw_data[offset+adjusted_col] = self._get_int(row, col)
                if col == 0 and not self._is_empty(row, 1):
                    print "ne: %s, N: %s" % (self._get_int(row, 0), self._get_int(row, 1))
                    print self._get_int(row, 0) + self._get_int(row, 1)
                    # if the event count has been changed, and the number of
                    # no events has been given, we need to update the total
                    self.raw_data[offset+1] = self._get_int(row, 0) + self._get_int(row, 1)
            else:
                # then column 1, i.e., "no event" has been edited. 
                no_events = self._get_int(row, col)
                index = offset+1
                print "setting %s to %s" % (index, self.raw_data[offset] + no_events)
                self.raw_data[index] = self.raw_data[offset] + no_events
            self._update_raw_data()
            self._update_data_table()
        self.check_for_consistencies()
        
        # @TODO refactor
        d = self._build_dict()
        meta_py_r.impute_two_by_two(d)
        
    def _build_dict(self):
        d =  dict(zip(["control.n.outcome", "control.N", "tx.n.outcome", "tx.N"], self.raw_data))
        print "\n!%s" % self.ma_unit.effects_dict[self.cur_effect]
        d["estimate"] = self.ma_unit.effects_dict[self.cur_effect]['est']
        print d["estimate"] == ""
        print d["estimate"] is None
        return d
        
    def check_for_consistencies(self):
        self.check_that_rows_sum()
    
    def check_that_rows_sum(self):
        for row in range(3):
            if self._row_is_populated(row):
                row_sum = 0
                for col in range(2):
                    row_sum += self._get_int(row, col)
                if not row_sum == self._get_int(row, 2):
                    self._color_row(row)
                    
    def check_that_cols_sum(self):
        # @TODO
        pass
        
    def _color_row(self, row):
        self.raw_data_table.blockSignals(True)
        error_color = QColor("red")
        for col in range(3):
            print "setting row: %s, col: %s" % (row, col)
            self.raw_data_table.item(row, col).setTextColor(error_color)
        self.raw_data_table.blockSignals(False)
        
    def _row_is_populated(self, row):
        return not True in [self._is_empty(row, col) for col in range(2)]
        
    def _update_data_table(self):        
        self.raw_data_table.blockSignals(True)
        # now compute the numbers with no events, if possible.
        # 
        # the raw data is of the form g_n / g_N where g_N is the *total* 
        # and g_n is the event count. thus no event = g_N - g_n.
        e1, n1, e2, n2 = [int(x) if x != "" else None for x in self.raw_data]
        print "updating raw data with:\n e1 = %s, n1 = %s, e2 = %s, n2 = %s" % \
                                            (e1, n1, e2, n2)
        no_events1, no_events2 = None, None
        
        #
        # @TODO this should probably be refactored.. kind of smells.
        #
        
        # also, instead of checking if None, check if None or "" (either way it's considered 'empty')
        if e1 is not None and n1 is not None and self._is_empty(0, 1):
            no_events1 = n1 - e1
            self.raw_data_table.setItem(0, 1, \
                                                        QTableWidgetItem(str(no_events1)))
                                                 
        if e2 is not None and n2 is not None and self._is_empty(1, 1):
            no_events2 = n2 - e2
            self.raw_data_table.setItem(1, 1, \
                                                        QTableWidgetItem(str(no_events2)))
            

        # total the totals (if possible)
        if n1 is not None and n2 is not None:
            self.raw_data_table.setItem(2, 2, \
                                                        QTableWidgetItem(str(n1 + n2)))

        # and the totals of *no* events
        if no_events1 is not None and no_events2 is not None:
            self.raw_data_table.setItem(2, 1, \
                                                        QTableWidgetItem(str(no_events1 + no_events2)))
                    
        # and now compute the sum of events
        if e1 is not None and e2 is not None:
            no_events_total = e1 + e2
            self.raw_data_table.setItem(2, 0, \
                                                        QTableWidgetItem(str(no_events_total)))
                
        self.raw_data_table.blockSignals(False)
        
    def _is_empty(self, i, j):
        val = self.raw_data_table.item(i,j)
        return val is None or val.text() == ""
        
    def _get_int(self, i, j):
        if not self._is_empty(i,j):
            return int(self.raw_data_table.item(i, j).text())
            
