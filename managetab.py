#    https://launchpad.net/wxbanker
#    managetab.py: Copyright 2007, 2008 Mike Rooney <wxbanker@rowk.com>
#
#    This file is part of wxBanker.
#
#    wxBanker is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    wxBanker is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with wxBanker.  If not, see <http://www.gnu.org/licenses/>.

import wx, wx.grid as gridlib
import datetime
from banker import float2str
from bankcontrols import AccountListCtrl, NewTransactionCtrl
import pubsub

#TODO: search control, for searching in currently displayed transactions

class ManagePanel(wx.Panel):
    """
    This panel contains the list of accounts on the left
    and the transaction panel on the right.
    """
    def __init__(self, parent, frame):
        wx.Panel.__init__(self, parent)
        self.frame = frame

        self.accountCtrl = accountCtrl = AccountListCtrl(self, frame)
        self.transactionPanel = transactionPanel = TransactionPanel(self, frame)

        mainSizer = wx.BoxSizer()
        mainSizer.Add(accountCtrl, 0, wx.ALL, 5)
        mainSizer.Add(transactionPanel, 1, wx.EXPAND|wx.ALL, 5)

        #subscribe to messages that interest us
        pubsub.Publisher().subscribe(self.onChangeAccount, "VIEW.ACCOUNT_CHANGED")

        #select the first item by default, if there are any
        #we use a CallLater to allow everything else to finish creation as well,
        #otherwise it won't get scrolled to the bottom initially as it should.
        accountCtrl.SelectVisibleItem(0)

        self.Sizer = mainSizer
        mainSizer.Layout()
        
        wx.CallLater(50, lambda: transactionPanel.transactionGrid.ensureVisible(-1))

    def onChangeAccount(self, message, accountName):
        self.transactionPanel.setTransactions(accountName)

    def getCurrentAccount(self):
        return self.accountCtrl.GetCurrentAccount()


class TransactionPanel(wx.Panel):
    def __init__(self, parent, frame):
        wx.Panel.__init__(self, parent)
        self.parent = parent
        self.frame = frame

        self.transactionGrid = transactionGrid = TransactionGrid(self, frame)
        self.newTransCtrl = newTransCtrl = NewTransactionCtrl(self, frame)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(transactionGrid, 1, wx.EXPAND)
        mainSizer.Add(newTransCtrl, 0, wx.EXPAND|wx.LEFT|wx.TOP, 5)

        self.Sizer = mainSizer
        mainSizer.Layout()

        self.Bind(wx.EVT_SIZE, self.transactionGrid.doResize)
        #self.Bind(wx.EVT_MAXIMIZE, self.doResize)

    def setTransactions(self, *args, **kwargs):
        self.transactionGrid.setTransactions(*args, **kwargs)


class MoneyCellRenderer(gridlib.PyGridCellRenderer):
    def __init__(self):
        gridlib.PyGridCellRenderer.__init__(self)

    def Draw(self, grid, attr, dc, rect, row, col, isSelected):
        dc.SetBackgroundMode(wx.SOLID)
        dc.SetBrush(wx.Brush(attr.GetBackgroundColour(), wx.SOLID))
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)
        dc.SetBackgroundMode(wx.TRANSPARENT)
        dc.SetFont(attr.GetFont())

        value = grid.GetCellValue(row, col)
        if value < 0:
            dc.SetTextForeground("RED")
        else:
            dc.SetTextForeground("BLACK")

        text = float2str(value)

        #right-align horizontal, center vertical
        w, h = dc.GetTextExtent(text)
        x = rect.x + (rect.width-w) - 1
        y = rect.y + (rect.height-h)/2

        dc.DrawText(text, x, y)

    def GetBestSize(self, grid, attr, dc, row, col):
        dc.SetFont(attr.GetFont())
        w, h = dc.GetTextExtent(float2str(grid.GetCellValue(row, col)))
        return wx.Size(w, h)

    def Clone(self):
        return MoneyCellRenderer()


class TransactionGrid(gridlib.Grid):
    def __init__(self, parent, frame):
        gridlib.Grid.__init__(self, parent)
        self.parent = parent
        self.frame = frame
        self.changeFrozen = False

        self.CreateGrid(0, 4)

        self.SetColLabelValue(0, "Date")
        self.SetColLabelValue(1, "Description")
        self.SetColLabelValue(2, "Amount")
        self.SetColLabelValue(3, "Total")

        self.Bind(gridlib.EVT_GRID_CELL_CHANGE, self.onCellChange)
        self.Bind(gridlib.EVT_GRID_LABEL_RIGHT_CLICK, self.onLabelRightClick)

        pubsub.Publisher().subscribe(self.onTransactionRemoved, "REMOVED TRANSACTION")
        pubsub.Publisher().subscribe(self.onTransactionAdded, "NEW TRANSACTION")
        # this causes a segfault on amount changes, that's cute
        #pubsub.Publisher().subscribe(self.onTransactionUpdated, "UPDATED TRANSACTION")

    def GetCellValue(self, row, col):
        """
        When we get the values of amount/total columns,
        we want the float values. So just give us them.
        """
        val = gridlib.Grid.GetCellValue(self, row, col)
        if col in [2,3]: #cols 2 and 3 and amount/total
            val = float(val)

        return val

    def SetCellValue(self, row, col, val):
        """
        When we set the values of amount/total columns,
        it expects a string but our values are floats,
        so just cast it for us.
        """
        if col in [2,3]: #cols 2 and 3 and amount/total
            val = str(val)

        return gridlib.Grid.SetCellValue(self, row, col, val)

    def onTransactionAdded(self, message, data):
        #ASSUMPTION: the transaction was of the current account
        self.setTransactions(self.Parent.Parent.getCurrentAccount())

    def onTransactionUpdated(self, message, data):
        #ASSUMPTION: the transaction was of the current account
        self.setTransactions(self.Parent.Parent.getCurrentAccount(), ensureVisible=None)

    def onLabelRightClick(self, event):
        row, col = event.Row, event.Col
        if col == -1 and row >= 0:
            ID = int(self.GetRowLabelValue(row))
            menu = wx.Menu()
            item = wx.MenuItem(menu, -1, "Remove this transaction")
            #TODO: use an images library to get the remove BMP
            #item.SetBitmap(images.getRemoveBitmap())
            menu.AppendItem(item)
            #bind the right click, show, and then destroy
            menu.Bind(wx.EVT_MENU, lambda e: self.onRemoveTransaction(row, ID))
            self.PopupMenu(menu)
            menu.Destroy()

    def onRemoveTransaction(self, row, ID):
        #remove the transaction from the bank
        self.frame.bank.removeTransaction(ID)

    def getRowFromID(self, ID):
        for i in range(self.GetNumberRows()):
            if int(self.GetRowLabelValue(i)) == ID:
                return i

    def onTransactionRemoved(self, topic, ID):
        row = self.getRowFromID(ID)
        if row is not None: # it may not have been from the current account
            #delete the row from our grid
            self.DeleteRows(row)
            #self.updateTotals(row)
            self.setTransactions(self.Parent.Parent.getCurrentAccount())

    def onCellChange(self, event):
        if not self.changeFrozen:
            uid = int(self.GetRowLabelValue(event.Row))
            value = self.GetCellValue(event.Row, event.Col)

            amount = desc = date = None
            refreshNeeded = False
            if event.Col == 0:
                #make a date
                m, d, y = [int(x) for x in value.split('/')]
                date = datetime.date(y, m, d)
                refreshNeeded = True
            elif event.Col == 1:
                #make a desc
                desc = value
            else:
                #make a float
                amount = value
                #update all the totals after and including this one
                self.updateTotals(event.Row)

            self.changeFrozen = True
            self.frame.bank.updateTransaction(uid, amount, desc, date)
            self.changeFrozen = False

            if refreshNeeded:
                #this is needed because otherwise the Grid will put the new value in,
                #even if event.Skip isn't called, for some reason I don't understand.
                #event.Veto() will cause the OLD value to be put in. so it has to be updated
                #after the event handlers (ie this function) finish.
                wx.CallLater(50, lambda: self.setTransactions(self.Parent.Parent.getCurrentAccount(), ensureVisible=None))

    def updateTotals(self, startingRow=0):
        """
        Instead of pulling all the data from the bank, just
        update the totals ourselves, starting at a given row.
        """
        if startingRow == 0:
            total = 0.0
        else:
            total = self.GetCellValue(startingRow-1, 3)

        row = startingRow
        lastRow = self.GetNumberRows()-1
        while row <= lastRow:
            amount = self.GetCellValue(row, 2)
            total += amount
            self.SetCellValue(row, 3, total)
            row += 1

    def setTransactions(self, accountName, ensureVisible=-1):
        if accountName is None:
            numRows = self.GetNumberRows()
            if numRows:
                self.DeleteRows(0, numRows)
            return

        transactions = self.frame.bank.getTransactionsFrom(accountName)
        #first, adjust the number of rows in the grid to fit
        rowsNeeded = len(transactions)
        rowsExisting = self.GetNumberRows()
        if rowsNeeded > rowsExisting:
            self.AppendRows(rowsNeeded-rowsExisting)
        elif rowsExisting > rowsNeeded:
            self.DeleteRows(0, rowsExisting-rowsNeeded)

        #now fill in all the values
        total = 0.0
        for i, transaction in enumerate(transactions):
            uid, amount, desc, date = transaction
            total += amount
            self.SetRowLabelValue(i, str(uid))
            self.SetCellValue(i, 0, date.strftime('%m/%d/%Y'))
            self.SetCellValue(i, 1, desc)
            self.SetCellValue(i, 2, amount)
            self.SetCellEditor(i, 2, gridlib.GridCellFloatEditor(precision=2))
            self.SetCellValue(i, 3, total)
            self.SetReadOnly(i, 3, True) #make the total read-only
            for col in range(2):
                self.SetCellAlignment(i, 2+col, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                self.SetCellRenderer(i, 2+col, MoneyCellRenderer())

            #make every other row a different color
            cellAttr = gridlib.GridCellAttr()
            if i%2:
                cellAttr.SetBackgroundColour(wx.Color(224,238,238))
            else:
                cellAttr.SetBackgroundColour(wx.WHITE)
            self.SetRowAttr(i, cellAttr)

        #resize
        self.doResize()

        #scroll to the last transaction
        if ensureVisible is not None:
            self.ClearSelection()
            self.ensureVisible(ensureVisible)
            
    def ensureVisible(self, index):
        """
        Make sure that a cell at a given index is shown.
        Negative indexes are allowed for pythonic purposes.
        """
        rows = self.GetNumberRows()
        if not rows:
            return
        
        if index < 0:
            #allow pythonic negative indexing: -1 for the last, -2 for 2nd last, etc.
            index = rows + index
        self.MakeCellVisible(index, 0)

    def doResize(self, event=None):
        """
        This method is called to resize the grid when the window is resized.
        Basically, it Autosizes all columns and then gives any remaining space
        to the Description column's width.
        """
        parent = self.GetParent()
        parent.Freeze()

        self.AutoSizeColumns()
        #parent.Sizer.RecalcSizes()
        parent.Layout()

        #the column which will be expanded
        expandCol = 1

        #calculate the total width of the other columns
        otherWidths = 0
        for i in range(self.GetNumberCols()):
            if i != expandCol:
                otherWidths += self.GetColSize(i)

        #add the width of the row label column
        otherWidths += self.RowLabelSize

        sbWidth = 30
        #if not self.IsVisible(0, 0): #there must be a scrollbar!
        #    sbWidth += wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X)
        #    #self.EnableScrolling(False, True)

        descWidth = self.Size[0] - otherWidths - sbWidth

        self.SetColSize(expandCol, descWidth)

        parent.Thaw()
        parent.Layout()

        if event:
            event.Skip()
