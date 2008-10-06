"""
>>> usd = USD()
>>> usd.float2str(1)
'$1.00'
>>> usd.float2str(-2.1)
'$-2.10'
>>> usd.float2str(-10.17)
'$-10.17'
>>> usd.float2str(-777)
'$-777.00'
>>> usd.float2str(12345.67)
'$12,345.67'
>>> usd.float2str(12345)
'$12,345.00'
>>> usd.float2str(-12345.67)
'$-12,345.67'
>>> usd.float2str(-12345.6)
'$-12,345.60'
>>> usd.float2str(-123456)
'$-123,456.00'
>>> usd.float2str(.01)
'$0.01'
>>> usd.float2str(.01, 8)
'   $0.01'
>>> usd.float2str(2.1-2.2+.1) #test to ensure no negative zeroes
'$0.00'

>>> usd.str2float('$1.00') == 1.0
True
>>> usd.str2float('$-2.10') == -2.1
True
>>> usd.str2float('$-10.17') == -10.17
True
>>> usd.str2float('$-777.00') == -777
True
>>> usd.str2float('$12,345.67') == 12345.67
True
>>> usd.str2float('$12,345.00') == 12345
True
>>> usd.str2float('$-12,345.67') == -12345.67
True
>>> usd.str2float('$-12,345.6') == -12345.6
True
>>> usd.str2float('$-123,456') == -123456
True
>>> usd.str2float('$0.01') == 0.01
True
>>> usd.str2float('   $0.01') == 0.01
True
"""

class BaseCurrency(object):
    def __init__(self):
        self.Symbol = ''
        self.SepChar = ','
        self.DecChar = '.'
        self.ShortName = ""
        self.LongName = ""
    
    def float2str(self, number, just=0):
        """
        Converts a float to a pleasing "money string".
        """
        # Step 1: Convert to a float with 2 decimal places.
        numStr = '%.2f' % number
        # Step 2: Don't display negative zeroes (LP: 250151).
        if numStr == '-0.00':
            numStr = '0.00'
        # Step 3: Use the proper decimal character.
        numStr = numStr.replace('.', self.DecChar)
        # Step 4: Add separating characters.
        if len(numStr) > 6 + numStr.find('-') + 1: # remember, Symbol is not added yet
            numStr = numStr[:len(numStr)-6] + self.SepChar + numStr[len(numStr)-6:]
        # Step 5: Add the currency symbol.
        numStr = self.Symbol + numStr
        # Step 6: Justify to the optional kwarg.
        numStr = numStr.rjust(just)
        # And return.
        return numStr

    def str2float(self, mstr):
        """
        Converts a pleasing "money string" to a float.
        """
        # Step 0: Strip off any stray spaces
        mstr = mstr.strip()
        # Step 1: Strip off the currency symbol
        mstr = mstr[len(self.Symbol):]
        # Step 2: Remove separators.
        mstr = mstr.replace(self.SepChar, '')
        # Step 3: Ensure decimal char is a period.
        mstr = mstr.replace(self.DecChar, '.')
        # Step 4: Conver to float
        floatval = float(mstr)
        # And return.
        return floatval


class USD(BaseCurrency):
    """
    United States Dollar currency.
    """
    def __init__(self):
        self.Symbol = '$'
        self.SepChar = ','
        self.DecChar = '.'
        self.ShortName = "USD"
        self.LongName = "United States Dollar"
    
if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
    