#!/usr/bin/env python
#
#    https://launchpad.net/wxbanker
#    bankobjects.py: Copyright 2007-2009 Mike Rooney <michael@wxbanker.org>
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

from wx.lib.pubsub import Publisher
import datetime
import bankexceptions, currencies, plotalgo, localization


class BankModel(object):
    def __init__(self, store, accountList):
        self.Store = store
        self.Accounts = accountList
        
        Publisher().subscribe(self.onCurrencyChanged, "user.currency_changed")
        
    def GetBalance(self):
        return self.Accounts.Balance
    
    def GetXTotals(self, numPoints):
        transactions = []
        for account in self.Accounts:
            transactions.extend(account.Transactions)
            
        return plotalgo.get(transactions, numPoints)
        
    def GetAccount(self, accountName):
        return self.Accounts.Get(accountName)
        
    def CreateAccount(self, accountName):
        return self.Accounts.Create(accountName)
    
    def RemoveAccount(self, accountName):
        return self.Accounts.Remove(accountName)
        
    def float2str(self, *args, **kwargs):
        """
        Handle representing floats as strings for non
        account-specific amounts, such as totals.
        """
        if len(self.Accounts) == 0:
            currency = currencies.CurrencyList[0]()
        else:
            currency = self.Accounts[0].Currency
            
        return currency.float2str(*args, **kwargs)
        
    def setCurrency(self, currencyIndex):
        self.Store.setCurrency(currencyIndex)
        #self.Currency = currencies.CurrencyList[currencyIndex]()
        Publisher().sendMessage("currency_changed", currencyIndex)
        
    def onCurrencyChanged(self, message):
        currencyIndex = message.data
        self.setCurrency(currencyIndex)
        
    def equals(self, other):
        return self.Accounts.equals(other.Accounts)

    Balance = property(GetBalance)

    
class AccountList(list):
    def __init__(self, store, accounts):
        list.__init__(self, accounts)
        # Make sure all the items know their parent list.
        for account in self:
            account.Parent = self
            
        self.Store = store
        
    def GetBalance(self):
        return sum([account.Balance for account in self])
        
    def AccountIndex(self, accountName):
        for i, account in enumerate(self):
            if account.Name == accountName:
                return i
            
        return -1
    
    def Get(self, accountName):
        index = self.AccountIndex(accountName)
        if index == -1:
            raise bankexceptions.InvalidAccountException(accountName)
        
        return self[index]
        
    def Create(self, accountName):
        # First, ensure an account by that name doesn't already exist.
        if self.AccountIndex(accountName) >= 0:
            raise bankexceptions.AccountAlreadyExistsException(accountName)
        
        account = self.Store.CreateAccount(accountName)
        # Make sure this account knows its parent.
        account.Parent = self
        self.append(account)
        return account
        
    def Remove(self, accountName):
        index = self.AccountIndex(accountName)
        if index == -1:
            raise bankexceptions.InvalidAccountException(accountName)
        
        account = self.pop(index)
        self.Store.RemoveAccount(account)
        Publisher.sendMessage("account.removed.%s"%accountName, account)

    def equals(self, other):
        if len(self) != len(other):
            return False
        for leftAccount, rightAccount in zip(self, other):
            if not leftAccount.equals(rightAccount):
                return False
            
        return True
            
    Balance = property(GetBalance)

    
class Account(object):
    def __init__(self, store, aID, name, currency=0, balance=0.0):
        self.Store = store
        self.ID = aID
        self._Name = name
        self._Transactions = None
        self.Currency = currencies.CurrencyList[currency]()
        self._Balance = balance
        
        Publisher.subscribe(self.onTransactionAmountChanged, "transaction.updated.amount")
        Publisher.sendMessage("account.created.%s" % name, self)
        
    def GetBalance(self):
        return self._Balance
    
    def SetBalance(self, newBalance):
        self._Balance = newBalance
        Publisher.sendMessage("account.balance changed.%s" % self.Name, self)
        
    def GetTransactions(self):
        if self._Transactions is None:
            self._Transactions = self.Store.getTransactionsFrom(self)
        
        return self._Transactions
        
    def GetName(self):
        return self._Name

    def SetName(self, name):
        index = self.Parent.AccountIndex(name)
        if index != -1:
            raise bankexceptions.AccountAlreadyExistsException(name)
    
        oldName = self._Name
        self._Name = name
        Publisher.sendMessage("account.renamed.%s"%oldName, (oldName, self))
        
    def Remove(self):
        self.Parent.Remove(self.Name)

    def AddTransaction(self, amount, description="", date=None, source=None):
        """
        Enter a transaction in this account, optionally making the opposite
        transaction in the source account first.
        """
        if source:
            if description:
                description = " (%s)" % description
            otherTrans = source.AddTransaction(-amount, _("Transfer to %s"%self.Name) + description, date)
            description = _("Transfer from %s"%source.Name) + description 
            
        partialTrans = Transaction(None, self, amount, description, date)
        self.Store.MakeTransaction(self, partialTrans)
        transaction = partialTrans
        
        # IMPROVEMENT: using .Transactions on an account which hasn't fetched its
        # transactions yet will cause it to fetch them all, which is silly to ADD
        # an account. Ideally have a more aware list from the start which knows
        # when it needs to be populated, and does so. It probably never stores any
        # items until then. For transfers this is wasteful on the other account.
        self.Transactions.append(transaction)
        
        Publisher.sendMessage("transaction.created.%s" % self.Name, transaction)
        
        # Update the balance.
        self.Balance += transaction.Amount
        
        if source:
            return transaction, otherTrans
        else:
            return transaction

    def RemoveTransaction(self, transaction):
        if transaction not in self.Transactions:
            raise bankexceptions.InvalidTransactionException("Transaction does not exist in account '%s'" % self.Name)
        
        self.Store.RemoveTransaction(transaction)
        Publisher.sendMessage("transaction.removed.%s"%self.Name, transaction)
        self.Transactions.remove(transaction)
        
        # Update the balance.
        self.Balance -= transaction.Amount
        
    def onTransactionAmountChanged(self, message):
        transaction, difference = message.data
        if transaction in self.Transactions:
            self.Balance += difference
        
    def float2str(self, *args, **kwargs):
        return self.Currency.float2str(*args, **kwargs)
        
    def __cmp__(self, other):
        return cmp(self.Name, other.Name)
    
    def equals(self, other):
        return (
            self.Name == other.Name and
            self.Balance == other.Balance and
            self.Currency == other.Currency and
            self.Transactions.equals(other.Transactions)
        )
    
    Name = property(GetName, SetName)
    Transactions = property(GetTransactions)
    Balance = property(GetBalance, SetBalance)
        
    
class TransactionList(list):
    def __init__(self, items=None):
        # list does not understand items=None apparently.
        if items is None:
            items = []
            
        list.__init__(self, items)
        
    def equals(self, other):
        if not len(self) == len(other):
            return False
        for leftTrans, rightTrans in zip(self, other):
            if not leftTrans.equals(rightTrans):
                return False
            
        return True

class Transaction(object):
    """
    An object which represents a transaction.
    
    Changes to this object get sent out via pubsub,
    typically causing the model to make the change.
    """
    def __init__(self, tID, parent, amount, description, date):
        self.IsFrozen = True
        
        self.ID = tID
        self.Parent = parent
        self.Date = date
        self.Description = description
        self.Amount = amount
        
        self.IsFrozen = False
        
    def GetDate(self):
        return self._Date
        
    def SetDate(self, date):
        self._Date = self._MassageDate(date)
            
        if not self.IsFrozen:
            Publisher.sendMessage("transaction.updated.date", (self, None))
            
    def _MassageDate(self, date):
        """
        Takes a date and returns a valid datetime.date object.
        `date` can be a datetime object, or a string.
        In the case of a string, valid separators are '-' and '/'.
        
        Abbreviated years will be converted into the "intended" year.
    
        >>> _MassageData = Transaction(None, None, 0, "", '2001/01/01')._MassageDate
        >>> _MassageData("2008-01-06")
        datetime.date(2008, 1, 6)
        >>> _MassageData("08-01-06")
        datetime.date(2008, 1, 6)
        >>> _MassageData("86-01-06")
        datetime.date(1986, 1, 6)
        >>> _MassageData("11-01-06")
        datetime.date(2011, 1, 6)
        >>> _MassageData("0-1-6")
        datetime.date(2000, 1, 6)
        >>> _MassageData("0/1/6")
        datetime.date(2000, 1, 6)
        >>> _MassageData(datetime.date(2008, 1, 6))
        datetime.date(2008, 1, 6)
        >>> _MassageData(None) == datetime.date.today()
        True
        """
        if date is None:
            return datetime.date.today()
        # The maximum number of years you can refer to in the future, using an abbreviation.
        # Ex: If it is 2008 and MAX_FUTURE_ABBR is 10, years 9-18 will become 2009-2018,
        # while 19-99 will become 1919-1999.
        MAX_FUTURE_ABBR = 10
        date = str(date) #if it is a datetime.date object, make it a Y-M-D string.
        date = date.replace('/', '-') # '-' is our standard assumed separator
        year, m, d = [int(x) for x in date.split("-")]
        if year < 100:
            currentYear = datetime.date.today().year
            currentAbr = currentYear % 100
            currentBase = currentYear / 100
            if year <= currentAbr + MAX_FUTURE_ABBR: #allow the user to reasonably refer to future years
                year += currentBase * 100
            else:
                year += (currentBase-1) * 100
        return datetime.date(year, m, d)
            
    def GetDescription(self):
        return self._Description

    def SetDescription(self, description):
        """Update the description, ensuring it is a string."""
        self._Description = str(description)
        
        if not self.IsFrozen:
            Publisher.sendMessage("transaction.updated.description", (self, None))
            
    def GetAmount(self):
        return self._Amount

    def SetAmount(self, amount):
        """Update the amount, ensuring it is a float."""
        if hasattr(self, "_Amount"):
            difference = amount - self._Amount
            
        self._Amount = float(amount)
        
        if not self.IsFrozen:
            Publisher.sendMessage("transaction.updated.amount", (self, difference))
            
    def Print(self):
        print "%i/%i/%i: %s -- %.2f" % (self.Date.year, self.Date.month, self.Date.day, self.Description, self.Amount)
            
    def __cmp__(self, other):
        return cmp(
            (self.Date, self.Amount, self.Description, self.Parent),
            (other.Date, other.Amount, other.Description, other.Parent)
        )
    
    def equals(self, other):
        assert isinstance(other, Transaction)
        return (
            self.Date == other.Date and
            self.Description == other.Description and
            self.Amount == other.Amount
        )
            
    Date = property(GetDate, SetDate)
    Description = property(GetDescription, SetDescription)
    Amount = property(GetAmount, SetAmount)
               
        
if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
