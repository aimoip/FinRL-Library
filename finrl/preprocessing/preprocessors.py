import numpy as np
import pandas as pd
from stockstats import StockDataFrame as Sdf
from finrl.config import config


class FeatureEngineer:
    """Provides methods for preprocessing the stock price data

    Attributes
    ----------
        df: DataFrame
            data downloaded from Yahoo API
            7 columns: A date, open, high, low, close, volume and tick symbol
            for the specified stock ticker
        use_technical_indicator : boolean
            we technical indicator or not
        tech_indicator_list : list
            a list of technical indicator names (modified from config.py)
        use_turbulence : boolean
            use turbulence index or not
        user_defined_feature:boolean
            user user defined features or not

    Methods
    -------
    preprocess_data()
        main method to do the feature engineering

    """
    def __init__(self, 
        df,
        use_technical_indicator=True,
        tech_indicator_list = config.TECHNICAL_INDICATORS_LIST,
        use_turbulence=False,
        user_defined_feature=False,
        ichimoko=False):

        self.df = df
        self.use_technical_indicator = use_technical_indicator
        self.tech_indicator_list = tech_indicator_list
        self.use_turbulence=use_turbulence
        self.user_defined_feature=user_defined_feature
        self.ichimoko=ichimoko

        #type_list = self._get_type_list(5)
        #self.__features = type_list
        #self.__data_columns = config.DEFAULT_DATA_COLUMNS + self.__features


    def preprocess_data(self):
        """main method to do the feature engineering
        @:param config: source dataframe
        @:return: a DataMatrices object
        """
        df = self.df.copy()

        # add technical indicators
        # stockstats require all 5 columns
        if (self.use_technical_indicator==True):
            # add technical indicators using stockstats
            df=self.add_technical_indicator(df)
            print("Successfully added technical indicators")

        # add turbulence index for multiple stock
        if self.use_turbulence==True:
            df = self.add_turbulence(df)
            print("Successfully added turbulence index")

        # add user defined feature
        if self.user_defined_feature == True:
            df = self.add_user_defined_feature(df)
            print("Successfully added user defined features")

       
        # fill the missing values at the beginning and the end
        df=df.fillna(method='bfill').fillna(method="ffill")
        return df

    def ichimoku(dataframe, conversion_line_period=9, base_line_periods=26,
             laggin_span=52, displacement=26):
    """
    Ichimoku cloud indicator
    Note: Do not use chikou_span for backtesting.
        It looks into the future, is not printed by most charting platforms.
        It is only useful for visual analysis
    :param dataframe: Dataframe containing OHLCV data
    :param conversion_line_period: Conversion line Period (defaults to 9)
    :param base_line_periods: Base line Periods (defaults to 26)
    :param laggin_span: Lagging span period
    :param displacement: Displacement (shift) - defaults to 26
    :return: Dict containing the following keys:
        tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, leading_senkou_span_a,
        leading_senkou_span_b, chikou_span, cloud_green, cloud_red
    """

    tenkan_sen = (dataframe['high'].rolling(window=conversion_line_period).max()
                  + dataframe['low'].rolling(window=conversion_line_period).min()) / 2

    kijun_sen = (dataframe['high'].rolling(window=base_line_periods).max()
                 + dataframe['low'].rolling(window=base_line_periods).min()) / 2

    leading_senkou_span_a = (tenkan_sen + kijun_sen) / 2

    leading_senkou_span_b = (dataframe['high'].rolling(window=laggin_span).max()
                             + dataframe['low'].rolling(window=laggin_span).min()) / 2

    senkou_span_a = leading_senkou_span_a.shift(displacement)

    senkou_span_b = leading_senkou_span_b.shift(displacement)

    chikou_span = dataframe['close'].shift(-displacement)

    cloud_green = (senkou_span_a > senkou_span_b)
    cloud_red = (senkou_span_b > senkou_span_a)

    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'leading_senkou_span_a': leading_senkou_span_a,
        'leading_senkou_span_b': leading_senkou_span_b,
        'chikou_span': chikou_span,
        'cloud_green': cloud_green,
        'cloud_red': cloud_red,
    }
    def add_technical_indicator(self, data):
        """
        calcualte technical indicators
        use stockstats package to add technical inidactors
        :param data: (df) pandas dataframe
        :return: (df) pandas dataframe
        """
        df = data.copy()
        stock = Sdf.retype(df.copy())
        unique_ticker = stock.tic.unique()

        for indicator in self.tech_indicator_list:
            indicator_df = pd.DataFrame()
            for i in range(len(unique_ticker)):
                try:
                    temp_indicator = stock[stock.tic == unique_ticker[i]][indicator]
                    temp_indicator= pd.DataFrame(temp_indicator)
                    indicator_df = indicator_df.append(temp_indicator, ignore_index=True)
                except Exception as e:
                    print(e)
            df[indicator] = indicator_df
        if ichimoko:
            df[['tenkan_sen']]=self.ichimoku(df)['tenkan_sen']
            df[['kijun_sen']]=self.ichimoku(df)['kijun_sen']
            df[['senkou_span_a']]=self.ichimoku(df)['senkou_span_a']
            df[['senkou_span_b']]=self.ichimoku(df)['senkou_span_b']
            df[['leading_senkou_span_a']]=self.ichimoku(df)['leading_senkou_span_a']
            df[['leading_senkou_span_b']]=self.ichimoku(df)['leading_senkou_span_b']
            #df[['chikou_span']]=self.ichimoku(df)['chikou_span']
            df[['cloud_green']]=self.ichimoku(df)['cloud_green']
            df[['cloud_red']]=self.ichimoku(df)['cloud_red']
        return df

    def add_user_defined_feature(self, data):
        """
         add user defined features
        :param data: (df) pandas dataframe
        :return: (df) pandas dataframe
        """          
        df = data.copy()
        df['daily_return']=df.close.pct_change(1)
        #df['return_lag_1']=df.close.pct_change(2)
        #df['return_lag_2']=df.close.pct_change(3)
        #df['return_lag_3']=df.close.pct_change(4)
        #df['return_lag_4']=df.close.pct_change(5)
        return df


    def add_turbulence(self, data):
        """
        add turbulence index from a precalcualted dataframe
        :param data: (df) pandas dataframe
        :return: (df) pandas dataframe
        """
        df = data.copy()
        turbulence_index = self.calcualte_turbulence(df)
        df = df.merge(turbulence_index, on='date')
        df = df.sort_values(['date','tic']).reset_index(drop=True)
        return df


    def calcualte_turbulence(self, data):
        """calculate turbulence index based on dow 30"""
        # can add other market assets
        df = data.copy()
        df_price_pivot=df.pivot(index='date', columns='tic', values='close')
        unique_date = df.date.unique()
        # start after a year
        start = 252
        turbulence_index = [0]*start
        #turbulence_index = [0]
        count=0
        for i in range(start,len(unique_date)):
            current_price = df_price_pivot[df_price_pivot.index == unique_date[i]]
            hist_price = df_price_pivot[[n in unique_date[0:i] for n in df_price_pivot.index ]]
            cov_temp = hist_price.cov()
            current_temp=(current_price - np.mean(hist_price,axis=0))
            temp = current_temp.values.dot(np.linalg.inv(cov_temp)).dot(current_temp.values.T)
            if temp>0:
                count+=1
                if count>2:
                    turbulence_temp = temp[0][0]
                else:
                    #avoid large outlier because of the calculation just begins
                    turbulence_temp=0
            else:
                turbulence_temp=0
            turbulence_index.append(turbulence_temp)
        
        
        turbulence_index = pd.DataFrame({'date':df_price_pivot.index,
                                         'turbulence':turbulence_index})
        return turbulence_index

    def _get_type_list(self, feature_number):
        """
        :param feature_number: an int indicates the number of features
        :return: a list of features n
        """
        if feature_number == 1:
            type_list = ["close"]
        elif feature_number == 2:
            type_list = ["close", "volume"]
            #raise NotImplementedError("the feature volume is not supported currently")
        elif feature_number == 3:
            type_list = ["close", "high", "low"]
        elif feature_number == 4:
            type_list = ["close", "high", "low", "open"]
        elif feature_number == 5:
            type_list = ["close", "high", "low", "open","volume"]  
        else:
            raise ValueError("feature number could not be %s" % feature_number)
        return type_list
