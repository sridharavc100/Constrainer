import pandas as pd
import numpy as np

def stationery_constraint(df,arr,capacitydf):

    code_to_remain_stationery = ['3','4','5','6','7','8','A','B','C','D','E','F','G','H']
    df.loc[:,'PlanningImpactCode']='None'
    for cnt in df[df['INTEGRATED_ACTIVITY_PLANNING_IMPACT_TYPE_CODE'].isin(code_to_remain_stationery)]['Order'].unique():
        ind = df[df['Order']==cnt].index
        df.loc[ind,'PlanningImpactCode']='stay'

    workorder_zpbl = df[( (df['ESD_WeekNumber'] == 0) | (df['Order User Status'].str.contains('ZPBL'))| (df['EXECUTION_CONDITION_CODE'].str.contains('SDTA')) | (df['PlanningImpactCode'].str.contains('stay'))  | (df['Order User Status'].str.contains('CAM'))) & (df['Order Type'] == '72FC') ]['Order'].unique()
    # Stagnant df
    stagnantdf = pd.DataFrame()
    for cnt in workorder_zpbl:
        stagnantdf = pd.concat([stagnantdf,df[df['Order'] == cnt]], axis=0)

    stagnantdf.loc[stagnantdf[stagnantdf['ESD_WeekNumber'] == 0].index,'Allocated'] = 91
    stagnantdf.loc[stagnantdf[stagnantdf['Order User Status'].str.contains('ZPBL', na=False)].index,'Allocated'] = 92
    stagnantdf.loc[stagnantdf[stagnantdf['EXECUTION_CONDITION_CODE'].str.contains('SDTA', na=False)].index,'Allocated'] = 93
    stagnantdf.loc[stagnantdf[stagnantdf['PlanningImpactCode'].str.contains('stay', na=False)].index,'Allocated'] = 94
    stagnantdf.loc[stagnantdf[stagnantdf['Order User Status'].str.contains('CAM', na=False)].index,'Allocated'] = 95

    stagnantdf['AllocatedReason'] = 'ZPBL/CAM/T0/SDTA/Op Constraint'

    # Reduction of Capacity by zpbl
    for i in workorder_zpbl:
        for cnt in range(0,50):
            for count in arr:
                val = df[ ((df['ESD_WeekNumber']==cnt) & (df['UpdatedWorkCenter']==count) & (df['Order Type'] == '72FC') & (df['Order'] == i))]['Work'].sum()
                capacitydf.loc[cnt,count] = capacitydf.loc[cnt,count] - val

    # Removing them from the df
    df=df[~df.index.isin(stagnantdf.index)]

    return df,stagnantdf,capacitydf


def pslevel_constraint(df,arr,capacitydf):
    # Dealing with WorkOrders
    #****************** PS COnstraints *******************

    listofallT4psdfwhole = df[ ((df['PSLevel'] == 'PS-1') |  (df['PSLevel'] == 'PS-2') |  (df['PSLevel'] == 'PS-3')) & (df['Order Type'] == '72FC') ]

    listofallT4psdfresidual = listofallT4psdfwhole[listofallT4psdfwhole['ESD_WeekNumber'] == listofallT4psdfwhole['LAFD_WeekNumber'] ]

    listofallT4psdf = listofallT4psdfwhole[listofallT4psdfwhole['ESD_WeekNumber'] < listofallT4psdfwhole['LAFD_WeekNumber'] ]
    listofallT4psdf['AlternateESD'] = listofallT4psdf['ESD_WeekNumber'] + np.ceil(0.8*(listofallT4psdf['LAFD_WeekNumber'] - listofallT4psdf['ESD_WeekNumber']))
    listofallT4psdf.loc[listofallT4psdf.index,'MoveReason'] = 'Changed due to PS 1-3'
    listofallT4psdf.loc[listofallT4psdf.index,'Allocated'] = 2

    # Reduce the capacity in the moved week.
    for i in listofallT4psdf['Order'].unique():
        for cnt in range(0,50):
            for count in arr:
                val = listofallT4psdf[ (listofallT4psdf['AlternateESD']==cnt) & (listofallT4psdf['UpdatedWorkCenter']==count) & (listofallT4psdf['Order Type'] == '72FC') & listofallT4psdf['Order'] == i]['Work'].sum()
                capacitydf.loc[cnt,count] = capacitydf.loc[cnt,count] - val

    # Removing them from the df
    df=df[~df.index.isin(listofallT4psdf.index)]

    # Moving them to alternate week - fixed case
    # processleveldf.loc[processleveldf[ processleveldf['ESD_WeekNumber'] <= 3].index,'AlternateESD'] = 5
    #****************** PS COnstraints *******************

    listofallT4psdfresidual.loc[listofallT4psdfresidual.index,'Allocated'] = 29
    listofallT4psdfresidual.loc[listofallT4psdfresidual.index,'PriorityFilling'] = ''
    # Removing them from the df
    df=df[~df.index.isin(listofallT4psdfresidual.index)]

    return df, listofallT4psdf, listofallT4psdfresidual, capacitydf


def eta_constraint(df,arr,capacitydf):
    #****************** ETA COnstraints - 2 *******************

    etadf1 = df[ (df['PSLevel'] == 'PS-4') & (( df['ESD_WeekNumber'] - df['ETA_WeekNumber'] ) < 3) & (df['ETA_WeekNumber'] + 3 <= df['LAFD_WeekNumber'])]

    # MAKD - Materials are received warehouse ! May not tell if it shipped or not.
    # E2Open - Material movement report -- alternate solution !! - Stephen Hopkins
    # GR may not give the right info that we need. It provides about goods in (GOM DC) - Has it been SHipped or not. 


    etadf1['AlternateESD'] = etadf1['ETA_WeekNumber'] + 3
    etadf1['Allocated'] = 3
    etadf1['MoveReason'] = 'ETA Constraint'
    etadf1['PriorityFilling'] = ''

    # Reduce the capacity in the moved week.
    for i in etadf1['Order'].unique():
        for cnt in range(0,50):
            for count in arr:
                val = etadf1[ (etadf1['AlternateESD']==cnt) & (etadf1['UpdatedWorkCenter']==count) & (etadf1['Order Type'] == '72FC') & etadf1['Order'] == i]['Work'].sum()
                capacitydf.loc[cnt,count] = capacitydf.loc[cnt,count] - val

    # Removing them from the df
    df=df[~df.index.isin(etadf1.index)]

    # Residual 
    etadf1Residual = df[ (df['PSLevel'] == 'PS-4') & (( df['ESD_WeekNumber'] - df['ETA_WeekNumber'] ) <3) ]
    etadf1Residual['AlternateESD'] = etadf1Residual['ESD_WeekNumber'] 
    etadf1Residual['Allocated'] = 39
    etadf1Residual['PriorityFilling'] = ''
    # Removing them from the df
    df=df[~df.index.isin(etadf1Residual.index)]

    return df, etadf1, etadf1Residual, capacitydf




    
    