
import pandas as pd
import matplotlib.pyplot as plt



# This function merges the suitability code with the work center description to make it uniform.

def integrate_with_suitabilitycode(rawdf, assetname):
    if assetname=='URSA':
        ind = rawdf[rawdf['SuitabilityCode']==23].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ACR/Instrument Technician'
        ind = rawdf[rawdf['SuitabilityCode']==15].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Electrician'
        ind = rawdf[rawdf['SuitabilityCode']==17].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ET/CAO'
        ind = rawdf[rawdf['SuitabilityCode']==29].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==30].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Ursa Utilities Crane Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==31].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Ursa Utilities Solar Mechanic'

    if assetname=='Olympus':
        ind = rawdf[rawdf['SuitabilityCode']==23].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ACR/Instrument Technician'
        ind = rawdf[rawdf['SuitabilityCode']==15].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Electrician'
        ind = rawdf[rawdf['SuitabilityCode']==17].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ET/CAO'
        ind = rawdf[rawdf['SuitabilityCode']==29].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==30].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Crane Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==31].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Turbine Mechanic'

    if assetname=='Auger':
        ind = rawdf[rawdf['SuitabilityCode']==23].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ACR/Instrument Technician'
        ind = rawdf[rawdf['SuitabilityCode']==15].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Electrician'
        ind = rawdf[rawdf['SuitabilityCode']==17].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'ET/CAO'
        ind = rawdf[rawdf['SuitabilityCode']==29].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==30].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Crane Mechanic'
        ind = rawdf[rawdf['SuitabilityCode']==31].index
        rawdf.loc[ind,'UpdatedWorkCenter'] = 'Turbine Mechanic'

    return rawdf
    

# This function generates process steps based on Dawson's file

def integrate_with_process_steps(df, process_step_file):
    # Condition 1  : OT
    ind = df[(df['Order Type'] == '72FP') | (df['Order Type'] == '72WP') | (df['Order Type'] == '71PO') | (
                df['Order Type'] == 'GEN')].index
    df.loc[ind, 'OT'] = 'P'
    ind = df[(df['Order Type'] != '72FP') & (df['Order Type'] != '72WP') & (df['Order Type'] != '71PO') & (
                df['Order Type'] != 'GEN') & (df['Order Type'].notnull())].index
    df.loc[ind, 'OT'] = 'C'

    # Condition 2  : Status
    ind = df[(df['Order User Status'].str.contains('INIT') == True)].index
    df.loc[ind, 'Status'] = 'C'
    ind = df[(df['Order User Status'].str.contains('INIT') == False) & (df['Order Type'].notnull())].index
    df.loc[ind, 'Status'] = 'R'

    # Condition 3  : EXEC
    ind = df[(df['Order User Status'].str.contains('EXEC') == True) | (
                df['Order User Status'].str.contains('SCHD') == True)].index
    df.loc[ind, 'EXEC'] = 'E'
    ind = df[(df['Order User Status'].str.contains('EXEC') == False) & (
                df['Order User Status'].str.contains('SCHD') == False) & (df['Order Type'].notnull())].index
    df.loc[ind, 'EXEC'] = 'F'

    # Condition 4  : WP
    df['WP'] = 'F'
    df.loc[df['Order User Status'].str.contains('WPOK', na=False), 'WP'] = 'O'
    df.loc[df['Order User Status'].str.contains('WP', na=False) & (df['WP'] != 'O'), 'WP'] = 'W'

    # Condition 5  : ZPM
    ind = df[(df['Order User Status'].str.contains('ZPMM') == True) | (
                df['Order User Status'].str.contains('ZPVS') == True)].index
    df.loc[ind, 'ZPM'] = 'Z'
    ind = df[(df['Order User Status'].str.contains('ZPMM') == False) & (
                df['Order User Status'].str.contains('ZPVS') == False) & (df['Order Type'].notnull())].index
    df.loc[ind, 'ZPM'] = 'F'

    # Condition 6  : SFIX
    ind = df[(df['Order User Status'].str.contains('SFIX') == True)].index
    df.loc[ind, 'SFIX'] = 'Z'
    ind = df[(df['Order User Status'].str.contains('SFIX') == False) & (df['Order Type'].notnull())].index
    df.loc[ind, 'SFIX'] = 'A'

    df['Code'] = df['OT'] + df['Status'] + df['EXEC'] + df['WP'] + df['ZPM'] + df['SFIX']

    #BATToolSourcedf = pd.read_excel(process_step_file, sheet_name='Work Order Compliance Data')
    BATToolSourcedf = pd.read_csv(process_step_file)
    
    #BATToolSourcedf.columns = BATToolSourcedf.iloc[0]
    # BATToolSourcedf = BATToolSourcedf[1:]

    for cnt in BATToolSourcedf.index:
        ind = df[df['Code'] == BATToolSourcedf.loc[cnt, 'Code']].index
        df.loc[ind, 'PSLevel'] = BATToolSourcedf.loc[cnt, 'Hand Off Point']

    print('\n\nPS LEVELS\n\n')
    print(df['PSLevel'].value_counts())
    print('Nulls :' + str(len(df[df['PSLevel'].isnull()])))

    return df

# Generate Weekise pslevel count

def weekwise_pslevels(gendf,weekname):
    psdf=pd.DataFrame()
    for cnt in range(0,50):
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-1')]
        psdf.loc[cnt,'PS1'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-2')]
        psdf.loc[cnt,'PS2'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-3')]
        psdf.loc[cnt,'PS3'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-4')]
        psdf.loc[cnt,'PS4'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'EXEC')]
        psdf.loc[cnt,'EXEC'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'].isnull())]
        psdf.loc[cnt,'Null'] = tempdf['Order'].nunique()

    psdf['Total'] = psdf['PS1'] + psdf['PS2']+ psdf['PS3']+psdf['PS4']+psdf['EXEC'] + psdf['Null']
    return psdf


def plotting_bar_graph(psdf,todisplay):
    plt.figure(figsize=(14, 8))
    plt.bar(psdf.index, psdf['PS1'], color='maroon')
    plt.bar(psdf.index, psdf['PS2'], bottom=psdf['PS1'], color='sienna')
    plt.bar(psdf.index, psdf['PS3'], bottom=psdf['PS1'] + psdf['PS2'], color='salmon')
    plt.bar(psdf.index, psdf['PS4'], bottom=psdf['PS1'] + psdf['PS2'] + psdf['PS3'], color='peachpuff')
    plt.bar(psdf.index, psdf['EXEC'], bottom=psdf['PS1'] + psdf['PS2'] + psdf['PS3'] + psdf['PS4'], color='g')
    plt.bar(psdf.index, psdf['Null'], bottom=psdf['PS1'] + psdf['PS2'] + psdf['PS3'] + psdf['PS4'] + psdf['EXEC'],
            color='r')

    plt.grid()
    plt.xlabel('WeekNumber')
    plt.ylabel('WorkOrders')
    plt.title('CM - WorkOrders - ' +todisplay )
    plt.legend(['PS1', 'PS2', 'PS3', 'PS4', 'EXEC', 'Null'])
    for i, v in enumerate(psdf['Total']):
        plt.text(psdf.index[i] - .5, v + 0.25, str(int(v)))

    return



def weekwise_pslevels_experiment(gendf,weekname):
    psdf=pd.DataFrame()
    for cnt in range(0,50):
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-1')  & (gendf['ESD_WeekNumber'] == gendf['AlternateESD'])]
        psdf.loc[cnt,'PS1'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-2')  & (gendf['ESD_WeekNumber'] == gendf['AlternateESD'])]
        psdf.loc[cnt,'PS2'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-3')  & (gendf['ESD_WeekNumber'] == gendf['AlternateESD'])]
        psdf.loc[cnt,'PS3'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-1')  & (gendf['ESD_WeekNumber'] != gendf['AlternateESD'])]
        psdf.loc[cnt,'PS1_Moved'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-2')  & (gendf['ESD_WeekNumber'] != gendf['AlternateESD'])]
        psdf.loc[cnt,'PS2_Moved'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-3')  & (gendf['ESD_WeekNumber'] != gendf['AlternateESD'])]
        psdf.loc[cnt,'PS3_Moved'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-4') &  (gendf['Allocated'] != 3)]
        psdf.loc[cnt,'PS4'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'PS-4') &  (gendf['Allocated'] == 3)]
        psdf.loc[cnt,'PS4_Moved'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'] == 'EXEC')]
        psdf.loc[cnt,'EXEC'] = tempdf['Order'].nunique()
        tempdf = gendf[(gendf[weekname] == cnt) & (gendf['PSLevel'].isnull())]
        psdf.loc[cnt,'Null'] = tempdf['Order'].nunique()

    psdf['Total'] = psdf['PS1'] + psdf['PS2']+ psdf['PS3']+psdf['PS4']+psdf['EXEC'] + psdf['Null'] + psdf['PS1_Moved'] + psdf['PS2_Moved'] + psdf['PS3_Moved'] + psdf['PS4_Moved']
    return psdf


def plotting_bar_graph_experiment(psdf):
    plt.figure(figsize=(14, 8))
    plt.bar(psdf.index, psdf['PS1'], color='maroon')
    plt.bar(psdf.index, psdf['PS1_Moved'], bottom=psdf['PS1'] , color='turquoise')

    plt.bar(psdf.index, psdf['PS2'], bottom=psdf['PS1']+ psdf['PS1_Moved'], color='sienna')
    plt.bar(psdf.index, psdf['PS2_Moved'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2'], color='k')

    plt.bar(psdf.index, psdf['PS3'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved'], color='salmon')
    plt.bar(psdf.index, psdf['PS3_Moved'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved']+psdf['PS3'], color='k')

    plt.bar(psdf.index, psdf['PS4'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved']+psdf['PS3']+psdf['PS3_Moved'], color='peachpuff')
    plt.bar(psdf.index, psdf['PS4_Moved'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved']+psdf['PS3']+psdf['PS3_Moved']+psdf['PS4'], color='burlywood')

    plt.bar(psdf.index, psdf['EXEC'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved']+psdf['PS3']+psdf['PS3_Moved']+psdf['PS4']+psdf['PS4_Moved'], color='g')
    plt.bar(psdf.index, psdf['Null'], bottom=psdf['PS1']+ psdf['PS1_Moved']+psdf['PS2']+psdf['PS2_Moved']+psdf['PS3']+psdf['PS3_Moved']+psdf['PS4']+psdf['PS4_Moved']+psdf['EXEC'],
            color='r')

    plt.grid()
    plt.xlabel('WeekNumber')
    plt.ylabel('WorkOrders')
    plt.title('CM - WorkOrders - After')
    plt.legend(['PS1', 'PS1_Moved','PS2','PS2_Moved', 'PS3','PS3_Moved', 'PS4', 'PS4_Moved','EXEC', 'Null'])
    for i, v in enumerate(psdf['Total']):
        plt.text(psdf.index[i] - .5, v + 0.25, str(int(v)))

    return