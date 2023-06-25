# This file contains the preprocessing required before allocation

import pandas as pd
import datetime
from datetime import timedelta
import math
import numpy as np


# This function loads capacity for that asset in a dictionary format

def load_capacity_info(rawfilewithpath):
    df = pd.read_csv(rawfilewithpath)
    return dict(zip(df.WorkCraft, df.Capacity))


# Update CapcityTrackingdataframe

def update_capacity_tracking_dataframe(cap_track_df, capdf,suff):
	tempdf = capdf.copy()
	tempdf = tempdf.add_suffix(suff)
	cap_track_df = pd.concat([cap_track_df,tempdf],axis=1,ignore_index=False)
	return cap_track_df
    
# Weekday Thursday = 3
# Weekday Wednesday = 2
# For URSA, Weekday is thursday

def datetime_to_previous_weekstart(original_datetime):
    th = 3
    if pd.isnull(original_datetime):
        return
    if original_datetime.weekday() >= th:
        return original_datetime + datetime.timedelta(days=th - original_datetime.weekday())
    else:
        return original_datetime + datetime.timedelta(days=-th - 1 - original_datetime.weekday())


def preprocessing(rawdf):
	# Interchaning Priorities

	rawdf['Priority'].replace('S','-1',inplace=True)
	rawdf['Priority'].replace('E','0',inplace=True)

	# Assigning Week Numbers to ESD
		
	rawdf['Earliest start date'] = pd.to_datetime(rawdf['Earliest start date'],errors='coerce')
	rawdf['nearestE'] = rawdf.apply(lambda row: datetime_to_previous_weekstart(row['Earliest start date']), axis=1)
	rawdf['Total_Days'] = ( rawdf['nearestE'] - datetime_to_previous_weekstart(datetime.datetime.today()) ).dt.days +1
	rawdf['WeekNumberE'] = (rawdf['Total_Days']/7) 
	rawdf['ESD_WeekNumber'] = rawdf['WeekNumberE'].apply(np.int)


	# # Assigning Week Numbers to LAFD

	rawdf['Latest Allowed Finish Date'] = pd.to_datetime(rawdf['Latest Allowed Finish Date'],errors='coerce')
	rawdf['nearestL'] = rawdf.apply(lambda row: datetime_to_previous_weekstart(row['Latest Allowed Finish Date']), axis=1)
	rawdf['Total_Days'] = ( rawdf['nearestL'] - datetime_to_previous_weekstart(datetime.datetime.today()) ).dt.days +1
	rawdf['WeekNumberL'] = (rawdf['Total_Days']/7) 
	interindex = rawdf[~rawdf['WeekNumberL'].isnull()].index
	rawdf.loc[interindex,'LAFD_WeekNumber'] = rawdf.loc[interindex,'WeekNumberL'].apply(math.ceil)

	# Dropping intermediate columns so that outputs looks fine
	rawdf = rawdf.drop(['nearestE','nearestL','WeekNumberE','WeekNumberL','Total_Days'],axis=1)

	# Defining the scope of the problem 
	# only 72FP
	ind = rawdf[ (rawdf['Order Type'] == '72FP') | (rawdf['Order Type'] == '72FC') | (rawdf['Order Type'] == 'GEN') | (rawdf['Order Type'] == 'ZADM')| (rawdf['Order Type'] == '71PO')].index
	rawdf.loc[set(rawdf.index) - set(ind),'Allocated'] = 999

	return rawdf


def postprocessing(rawdf):
	# Explanation of Allocated Codes
	rawdf['Constraint'] = ''
	rawdf.loc[rawdf[rawdf['Allocated']==0].index,'Constraint'] = 'No Change - Schedulable'
	rawdf.loc[rawdf[ (rawdf['Allocated']==0) & (rawdf['MovedOut']==1) ].index,'Constraint'] = 'Change - Capacity Constraint overcome by Moving WO'
	inn =  rawdf[(rawdf['Allocated']==1) & (rawdf['UnAllocatedReason'].str.contains('ESD') )].index
	rawdf.loc[inn,'Constraint'] = 'No Change - LAFD / Basic Start Date (BSD) Issue'
	inn =  rawdf[(rawdf['Allocated']==1) & (rawdf['UnAllocatedReason'].str.contains('Bundling') )].index
	rawdf.loc[inn,'Constraint'] = 'No Change - Capacity Constraint due to LAFD'
	rawdf.loc[rawdf[rawdf['Allocated']==39].index,'Constraint'] = 'No Change - LAFD / Estimated Time of Arrival (ETA) Issue'
	rawdf.loc[rawdf[rawdf['Allocated']==29].index,'Constraint'] = 'No Change - LAFD / Process Step (PS) Issue'
	rawdf.loc[rawdf[rawdf['Allocated']==2].index,'Constraint'] = 'Change - Process Level Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==3].index,'Constraint'] = 'Change - ETA Constraint'
	
	# rawdf.loc[rawdf[rawdf['Allocated']==9].index,'Constraint'] = 'No Change - ZPBL/CAM/T0/SDTA/Op Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==91].index,'Constraint'] = 'No Change - T0 Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==92].index,'Constraint'] = 'No Change - ZPBL Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==93].index,'Constraint'] = 'No Change - SDTA Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==94].index,'Constraint'] = 'No Change - System Condition Constraint'
	rawdf.loc[rawdf[rawdf['Allocated']==95].index,'Constraint'] = 'No Change - CAM Constraint'

	rawdf.loc[rawdf[rawdf['Allocated']==999].index,'Constraint'] = 'No Change - Out of Scope'

	# Is the integrity of the work order preserved ? If not preserve it with Out of Scope Items
	for cnt in rawdf['Order'].unique():
		if len(rawdf[rawdf['Order']==cnt]['ESD_WeekNumber'].unique()) <= 1 : 
			if len(rawdf[rawdf['Order']==cnt]['AlternateESD'].unique()) > 1 :
				tochange = rawdf[rawdf['Order']==cnt]['AlternateESD'].max()
				rawdf.loc[rawdf[rawdf['Order']==cnt].index,'AlternateESD'] = tochange
				
	return rawdf
	

def postprocessingcapacity(df,capacitytrackingdf,arr):
	

	# Total Hours - Includes PMs, CMs and all work order types
	for arr_count in arr:
		capacitytrackingdf[arr_count+'_TotalRequirement'] = ''
		tempdf = df[df['UpdatedWorkCenter']==arr_count].groupby(by='ESD_WeekNumber').sum()['Work']
		for cnt in capacitytrackingdf.index:
			if cnt in tempdf.index:
				capacitytrackingdf.loc[cnt,arr_count+'_TotalRequirement'] = tempdf.loc[cnt]

	# # Includes only CMs which needed to be performed
	for arr_count in arr:
		capacitytrackingdf[arr_count+'_CMRequirement'] = ''
		tempdf = df[(df['UpdatedWorkCenter']==arr_count) & (df['Order Type']=='72FC') & ( (df['Constraint']=='Change - Capacity Constraint overcome by Moving WO') | (df['Constraint']=='No Change - Schedulable') | (df['Constraint']=='No Change - Capacity Constraint due to LAFD')) ].groupby(by='ESD_WeekNumber').sum()['Work']
		for cnt in capacitytrackingdf.index:
			if cnt in tempdf.index:
				capacitytrackingdf.loc[cnt,arr_count+'_CMRequirement'] = tempdf.loc[cnt]
	

	## After Optimization
	## Schedulable
	for arr_count in arr:
		capacitytrackingdf[arr_count+'_Executable_WithoutMove_AfterOptimization'] = ''
		tempdf = df[(df['UpdatedWorkCenter']==arr_count) & (df['Order Type']=='72FC') & (  (df['Constraint']=='No Change - Schedulable') ) ].groupby(by='AlternateESD').sum()['Work']
		for cnt in capacitytrackingdf.index:
			if cnt in tempdf.index:
				capacitytrackingdf.loc[cnt,arr_count+'_Executable_WithoutMove_AfterOptimization'] = tempdf.loc[cnt]


	## Moved and Schedulable
	for arr_count in arr:
		capacitytrackingdf[arr_count+'_Executable_WithMove_AfterOptimization'] = ''
		tempdf = df[(df['UpdatedWorkCenter']==arr_count) & (df['Order Type']=='72FC') & (  (df['Constraint']=='Change - Capacity Constraint overcome by Moving WO') ) ].groupby(by='AlternateESD').sum()['Work']
		for cnt in capacitytrackingdf.index:
			if cnt in tempdf.index:
				capacitytrackingdf.loc[cnt,arr_count+'_Executable_WithMove_AfterOptimization'] = tempdf.loc[cnt]	

	## UnMoved
	for arr_count in arr:
		capacitytrackingdf[arr_count+'_NonExecutable_AfterOptimization'] = ''
		tempdf = df[(df['UpdatedWorkCenter']==arr_count) & (df['Order Type']=='72FC') & (  (df['Constraint']=='No Change - Capacity Constraint due to LAFD') ) ].groupby(by='AlternateESD').sum()['Work']
		for cnt in capacitytrackingdf.index:
			if cnt in tempdf.index:
				capacitytrackingdf.loc[cnt,arr_count+'_NonExecutable_AfterOptimization'] = tempdf.loc[cnt]	

	return capacitytrackingdf

	





