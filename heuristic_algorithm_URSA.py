# Loading the relevant libraries

import pandas as pd
import datetime
import math
import numpy as np
import matplotlib.pyplot as plt
import SuitabilityCode as SC
import processing_utilities as pu
import constraints as cons
import allocation as allofcm
import warnings
warnings.filterwarnings('ignore')
import azureml.core
from azureml.core import Workspace, Dataset, Environment, Datastore
from azureml.core import Run
from datetime import timedelta


 # Load the workspace from the saved config file
ws = Workspace.get(name="eunmldevamlwsgom2",subscription_id='cf11c61d-e6ca-4f6b-b8df-d2a77e8a4d04',           resource_group='SEQ00963-NPRD-EUN-MLDEV-AML-gom2')
print('Ready to use Azure ML {} to work with {}'.format(azureml.core.VERSION, ws.name))
run = Run.get_context()

# Configuration Settings
# Merging with suitability code or just use raw file
is_suitability_code_integration = 'True'
# assetname = 'Auger'
assetname = 'URSA'
# assetname = 'Olympus'
totalweeks = 50

# Get the datastores available
dataset = Dataset.get_by_name(ws, name=assetname+'_Backlog')
rawdf = dataset.to_pandas_dataframe()


# Process step File needed to map the code
process_step_file = 'BAT Tool Source.csv'

rawdf['UpdatedWorkCenter'] = rawdf['WORK_CENTER_DESCRIPTION']
rawdf.rename(columns = {'CONCAT_USER_STATUS':'Order User Status'}, inplace = True)
rawdf.rename(columns = {'WORK_ORDER_TYPE_CODE':'Order Type'}, inplace = True)
rawdf.rename(columns = {'PLANNED_WORK':'Work'}, inplace = True)
rawdf.rename(columns = {'BASIC_START_DATE':'Earliest start date'}, inplace = True)
rawdf.rename(columns = {'PRIORITY_CODE':'Priority'}, inplace = True)
rawdf.rename(columns = {'LATEST_ALLOWABLE_FINISH_DATE':'Latest Allowed Finish Date'}, inplace = True)
rawdf.rename(columns = {'WORK_ORDER_SRC_ID':'Order'}, inplace = True)

if is_suitability_code_integration =='True':
    # Merging Suitability and updating work centers
    rawdf = SC.integrate_with_suitabilitycode(rawdf,assetname)


# Adding the PS Levels
rawdf = SC.integrate_with_process_steps(rawdf,process_step_file)


# Loading the capacity for URSA for the critical work crafts
if assetname=='URSA':
    capacityfile_withpath = 'ursa_capacity.csv'
if assetname=='Olympus':
    capacityfile_withpath = 'Olympus_capacity.csv'
if assetname=='Auger':
    capacityfile_withpath = 'auger_capacity.csv'


capacitydf = pd.read_csv(capacityfile_withpath)
capacitydf.set_index(['Week'], inplace=True)

# PreProcessing
# URSA
rawdf = pu.preprocessing(rawdf)

# Initialize CapcityTrackingdataframe
capacitytrackingdf = capacitydf.copy()


# Concentrating only the important WOs

if assetname == 'URSA':
    arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Ursa Utilities Crane Mechanic','Ursa Utilities Solar Mechanic','Ursa Bilfinger Maintenance Crew']

if assetname == 'Olympus':
    arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Crane Mechanic','Turbine Mechanic','Olympus Bilfinger Maintenance Crew']

if assetname == 'Auger':
    arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Crane Mechanic','Auger Solar Mechanic','Auger Bilfinger Maintenance Crew']

# Constraint 1 ***************

# ZPBL Constraint - CAM Constraint - T0 - SDTA-Opr Constraint
rawdf,stagnantdf,capacitydf = cons.stationery_constraint(rawdf,arr,capacitydf)
# Update CapcityTrackingdataframe
capacitytrackingdf = pu.update_capacity_tracking_dataframe(capacitytrackingdf, capacitydf,'_fixed_constraints')


df = rawdf[rawdf['Allocated'] != 999]
df = df.dropna(subset=['Work','Earliest start date'],axis=0)


# Scoping the constrainer_1
df = df[df['ESD_WeekNumber'] >=0 ]
df = df[df['ESD_WeekNumber'] <=50 ]
df = df[df['UpdatedWorkCenter'].isin(arr)]
rawdf.loc[set(rawdf.index) - set(df.index),'Allocated'] = 999


# Initial allocation

df['Allocated'] = 1
df['AllocatedReason'] = ''
df['MoveReason'] = ''
df['Capreqd'] = ''
df['UnAllocatedReason'] = ''
df['PriorityFilling'] = ''
df['AlternateESD'] = df['ESD_WeekNumber']




# Converting ETA to Weeknumber
        
df['ETADate'] = pd.to_datetime(df['ETADate'],errors='coerce')
df['nearestE'] = df.apply(lambda row: pu.datetime_to_previous_weekstart(row['ETADate']), axis=1)
df['Total_Days'] = ( df['nearestE'] - pu.datetime_to_previous_weekstart(datetime.datetime.today()) ).dt.days +1
df['WeekNumberE'] = (df['Total_Days']/7) 
interindex = df[~df['WeekNumberE'].isnull()].index
df.loc[interindex,'ETA_WeekNumber'] = df.loc[interindex,'WeekNumberE'].apply(np.int)


# Dropping intermediate columns so that outputs looks fine
df = df.drop(['nearestE','WeekNumberE','Total_Days'],axis=1)



# Constraint 2 #
#PS COnstraints 
df, listofallT4psdf, listofallT4psdfresidual, capacitydf = cons.pslevel_constraint(df,arr,capacitydf)

# Constriant 3 #
# ETA Constraint
df, etadf1, etadf1Residual, capacitydf = cons.eta_constraint(df,arr,capacitydf)
# Update CapcityTrackingdataframe
capacitytrackingdf = pu.update_capacity_tracking_dataframe(capacitytrackingdf, capacitydf,'_ps_eta')

# Reduction of Capacity by PMs, PO , GEN, ZADM
for cnt in range(0,50):
    for count in arr:
        val = df[ (df['ESD_WeekNumber']==cnt) & (df['UpdatedWorkCenter']==count) & ( (df['Order Type'] == '72FP') | (df['Order Type'] == 'GEN') | (df['Order Type'] == 'ZADM')| (df['Order Type'] == '71PO'))]['Work'].sum()
        capacitydf.loc[cnt,count] = capacitydf.loc[cnt,count] - val

# Update CapcityTrackingdataframe
capacitytrackingdf = pu.update_capacity_tracking_dataframe(capacitytrackingdf, capacitydf,'_Limit')

# Capacity Requirement for the CMs
CMcapacityreqdf = pd.DataFrame()
for cnt in range(0,50):
    for count in arr:
        val = df[ (df['ESD_WeekNumber']==cnt) & (df['UpdatedWorkCenter']==count) &  (df['Order Type'] == '72FC') ]['Work'].sum()
        CMcapacityreqdf.loc[cnt,count] = val

# Update CapcityTrackingdataframe
capacitytrackingdf = pu.update_capacity_tracking_dataframe(capacitytrackingdf, CMcapacityreqdf,'_Capacity_Reqd_CM_Before')

FCdf,validation_matrix,FPdf,unallocdf,capacitydf = allofcm.allocation_of_cm(df,capacitydf,totalweeks)

# Going back to df 

df.loc[FCdf.index,:] = FCdf.loc[FCdf.index,:]
df = pd.concat([df,listofallT4psdf], axis=0)
# df = pd.concat([df,etadf], axis=0)
df = pd.concat([df,etadf1], axis=0)
# df = pd.concat([df,etadf3], axis=0)
df = pd.concat([df,etadf1Residual], axis=0)
# df = pd.concat([df,etadf3Residual], axis=0)
df = pd.concat([df,listofallT4psdfresidual], axis=0)

rawdf = pd.concat([rawdf,stagnantdf], axis=0)
df.loc[FPdf.index,:] = FPdf.loc[FPdf.index,:]

df.loc[:,'MoveReason']  = ' '

inde = df[ ((df['ESD_WeekNumber'] != df['AlternateESD']) & (df['Allocated'] == 0) & (df['AlternateESD'] <= df['LAFD_WeekNumber']) ) ].index
df.loc[inde,'MovedOut'] = 1
df.loc[inde,'MoveReason']  = 'Moved from the scheduled week to meet the capacity for the WO' 

inde = df[ (df['Allocated'] == 2) ].index
df.loc[inde,'MovedOut'] = 1
df.loc[inde,'MoveReason']  = 'PS 1-3 Constraint. Any PS 1-3 WOs moved to 0.8 times LAFD'

inde = df[ (df['Allocated'] == 3) ].index
df.loc[inde,'MovedOut'] = 1
df.loc[inde,'MoveReason']  = 'ETA Constraint '

inde = df[ (df['Allocated'] == 39) ].index
df.loc[inde,'MoveReason']  = 'ETA-Unmovable'

inde = df[ (df['Allocated'] == 29) ].index
df.loc[inde,'MoveReason']  = 'PS1-3 Unmovable'


# Capacity Requirement for the CMs after optimization
CMcapacityreqdf_after = pd.DataFrame()
for cnt in range(0,50):
    for count in arr:
        val = df[ (df['AlternateESD']==cnt) & (df['UpdatedWorkCenter']==count)& (df['Allocated']==0) &  (df['Order Type'] == '72FC') ]['Work'].sum()
        CMcapacityreqdf_after.loc[cnt,count] = val

# Update CapcityTrackingdataframe
capacitytrackingdf = pu.update_capacity_tracking_dataframe(capacitytrackingdf, CMcapacityreqdf_after,'_Capacity_Reqd_CM_After')


# Inserting the column at the beginning in the DataFrame
# capacitytrackingdf.insert(loc = 0, column = 'Week', value = np.arange(0,len(capacitytrackingdf)))
capacitytrackingdf.to_csv(assetname+'_CapacityTracking.csv')

addncols = list(set(df.columns)-set(rawdf.columns))
for cnt in addncols:
    rawdf[cnt]=''
rawdf.loc[df.index,:] = df.loc[df.index,:]

# PostProcessing
rawdf = pu.postprocessing(rawdf)

# Update the Validation_Matrix
# WOs which are Schedulable
schwo = rawdf[rawdf['Constraint'].str.contains('Schedulable')]['Order'].unique()
for wono in schwo:
    ind = validation_matrix[validation_matrix['WO']==wono].index
    validation_matrix.loc[ind,'Constraint'] = 'No Change - Schedulable'

schmvwo = rawdf[rawdf['Constraint'].str.contains('Moving WO')]['Order'].unique()
for wono in schmvwo:
    ind = validation_matrix[validation_matrix['WO']==wono].index
    validation_matrix.loc[ind,'Constraint'] = 'Change - Capacity Constraint overcome by Moving WO'
    
schimwo = rawdf[rawdf['Constraint'].str.contains('Capacity Constraint - Immovable')]['Order'].unique()
for wono in schimwo:
    ind = validation_matrix[validation_matrix['WO']==wono].index
    validation_matrix.loc[ind,'Constraint'] = 'No Change - Capacity Constraint due to LAFD'


# # # Data Egestion to the current optimization blob
tem = rawdf.drop(columns = ['ETADate'])
defdatastore = ws.get_default_datastore()
# Register the dataset
ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=tem, 
        name=assetname+'_AfterOptimization', 
        description=assetname+'_AfterOptimization',
        target=defdatastore
    )

# Register the capacity dataframe
# New column to be added in capacity tracking
capacitytrackingdf = pu.postprocessingcapacity(rawdf,capacitytrackingdf,arr)

 
# Inserting the column at the beginning in the DataFrame
capacitytrackingdf.insert(loc = 0, column = 'Week', value = np.arange(0,len(capacitytrackingdf)))

ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=capacitytrackingdf, 
        name=assetname+'_CapacityMatrix', 
        description=assetname+'_CapacityMatrix',
        target=defdatastore
    )


ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=validation_matrix, 
        name=assetname+'_ValidationMatrix', 
        description=assetname+'_ValidationMatrix',
        target=defdatastore
    )





