import azureml.core
import pandas as pd
from azureml.core import Workspace, Dataset, Environment, Datastore
from azureml.core import Run
import utils
# To convert the unloading point to datetime
from dateutil.parser import parse

# Asset Choice
asset_name = 'URSA'

def is_date(string, fuzzy=True):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    
def processETAdate(unloadingdf):
    datelist = []
    for cnt in range(0,len(unloadingdf)):
        strtocheck = str(unloadingdf.loc[unloadingdf.index[cnt],'RESERVATION_UNLOADING_POINT'])
        if is_date(strtocheck) == True :
            datelist.append(parse(strtocheck,fuzzy=True))
    if len(datelist) > 0:
        return max(datelist),len(datelist)
    else:
        return None,None
        
    
        

    # Load the workspace from the saved config file
ws = Workspace.get(name="eunmldevamlwsgom2", subscription_id='cf11c61d-e6ca-4f6b-b8df-d2a77e8a4d04',resource_group='SEQ00963-NPRD-EUN-MLDEV-AML-gom2')
print('Ready to use Azure ML {} to work with {}'.format(azureml.core.VERSION, ws.name))
run = Run.get_context()

# Loading the Workspace

print(ws.name, ws.resource_group, ws.location, ws.subscription_id, sep='\n')


# Loading the data store


datastore = Datastore.get(workspace=ws, datastore_name="aif_gom")



# Query Name : Loading only the FC and FP 
# 810 ursa
# OLY Olympus
# Date : From this week till end of the year.
# /****** Script for SelectTopNRows command from SSMS  ******/
stringtorun = "SELECT A.ID, A.WORK_ORDER_SRC_ID, A.FACILITY_ID, A.PLANNER_GROUP_CODE, A.MAINTENANCE_PLANNER_GROUP_NAME, A.ASSET_DOMAIN_CODE, A.WBS_ID, A.WBS_CODE, A.WORK_ORDER_NAME, A.BASIC_START_DATE, A.BASIC_START_DATETIME, A.BASIC_END_DATE, A.SCHEDULED_START_DATE, A.BASIC_END_DATETIME, A.SCHEDULED_FINISH_DATE, A.ORIGINAL_LATEST_ALLOWABLE_FINISH_DATE, A.WORK_ORDER_TYPE_CODE, A.LATEST_ALLOWABLE_FINISH_DATE, A.SCHEDULED_START_DATETIME, A.SCHEDULED_FINISH_DATETIME, A.PLANT_CODE, A.FUNCTIONAL_LOCATION, A.ABC_INDICATOR, A.ITEM_SHORT_TEXT, A.MAIN_WORK_CENTER, A.MAIN_WORK_CENTER_DESCRIPTION, A.CONCAT_SYSTEM_STATUS, A.CONCAT_USER_STATUS, A.PRIORITY_CODE, A.SUPERIOR_ACTIVITY, A.WORK_ORDER_CREATED_DATE, A.LATEST_ALLOWABLE_START_DATE, A.ORIGINAL_LATEST_ALLOWABLE_START_DATE, A.WBS_SRC_ID, A.WORK_ORDER_DESCRIPTION, A.WORK_ORDER_REQUESTER_NAME, A.ESTIMATED_COST, B.PLANNED_WORK, B.PLANNED_WORK_UNIT_OF_MEASURE, B.WORK_ACTIVITY_COUNTER, B.WORK_CENTER, B.WORK_CENTER_DESCRIPTION, B.WORK_ACTIVITY_NUMBER, B.INTEGRATED_ACTIVITY_PLANNING_IMPACT_TYPE_CODE FROM DM_WORK.FACT_WORK_ORDER AS A LEFT JOIN DM_WORK.FACT_WORK_OPERATION AS B ON A.ID = B.WORK_ORDER_ID WHERE SCHEDULED_START_DATE >= '4/1/2023' AND PLANNER_GROUP_CODE = '810'"
print(stringtorun)


from azureml.data.datapath import DataPath

query = DataPath(datastore,stringtorun)
tabular = Dataset.Tabular.from_sql_query(query, query_timeout=300)
df = tabular.to_pandas_dataframe()
print(df.shape)

    # Unloading Point
stringtorun = "SELECT A.ID, A.WORK_ORDER_SRC_ID, C.WORK_ORDER_ID,C.WORK_ORDER_NUMBER, C.CREATION_DATETIME, C.WORK_ORDER_OPERATION_NUMBER,  C.RESERVATION_UNLOADING_POINT FROM DM_WORK.FACT_WORK_ORDER AS A LEFT JOIN DM_SUPPLY_CHAIN.FACT_RESERVATION_REQUIREMENT AS C ON A.WORK_ORDER_SRC_ID = C.WORK_ORDER_NUMBER WHERE SCHEDULED_START_DATE >= '1/1/2023' AND PLANNER_GROUP_CODE = '810'" 
query = DataPath(datastore,stringtorun)
tabular = Dataset.Tabular.from_sql_query(query, query_timeout=300)
uldf = tabular.to_pandas_dataframe()
print(df.shape)

currin = pd.DataFrame()
for i in uldf['WORK_ORDER_NUMBER'].unique():
    resdf = uldf[uldf['WORK_ORDER_NUMBER']==i]
    for j in resdf['WORK_ORDER_OPERATION_NUMBER'].unique():
        actdf = resdf[resdf['WORK_ORDER_OPERATION_NUMBER']==j]
        if actdf['RESERVATION_UNLOADING_POINT'].str.contains('ETA').any():
            findf = actdf[actdf['RESERVATION_UNLOADING_POINT'].str.contains('ETA')]
            ulp,N = processETAdate(findf)          
            wo = findf.loc[findf.index[-1],'WORK_ORDER_NUMBER']
            ac = findf.loc[findf.index[-1],'WORK_ORDER_OPERATION_NUMBER']
            currin = df[(df['WORK_ORDER_SRC_ID']==wo) & (df['WORK_ACTIVITY_NUMBER']==ac)]
            if len(currin) > 0:
                df.loc[currin.index[0],'ETADate'] = ulp
                df.loc[currin.index[0],'RESERVATION_UNLOADING_POINT_Entries'] = N

    # Suitability
stringtorun = 'SELECT SUITABILITY_CODE,WORK_CENTER_LOCATION_NAME, WORK_CENTER_NAME,WORK_CENTER_CODE,PLANT FROM DM_WORK.DIM_WORK_CENTER'
query = DataPath(datastore,stringtorun)
tabular = Dataset.Tabular.from_sql_query(query, query_timeout=300)
suitability_info = tabular.to_pandas_dataframe()


suitability_info.to_csv('suitability_info.csv')

for cnt in df['WORK_CENTER'].unique():
    if cnt != None:
        code = suitability_info[suitability_info['WORK_CENTER_CODE'].str.contains(cnt)]['SUITABILITY_CODE'].unique()
#         if cnt=='426MECH':
#         print(cnt,code)
#         if len(code)<2:
        subdf = df[df['WORK_CENTER']==cnt]
        df.loc[subdf.index,'SuitabilityCode'] = pd.to_numeric(code[0], errors='coerce')


# Include SDTA from FACT NOTIFICAITON
stringtorun = "SELECT WORK_ORDER_NUMBER, EXECUTION_CONDITION_CODE , MAINTENANCE_PLANNER_GROUP FROM DM_WORK.FACT_WORK_NOTIFICATION WHERE MAINTENANCE_PLANNER_GROUP='810'"
query = DataPath(datastore,stringtorun)
tabular = Dataset.Tabular.from_sql_query(query, query_timeout=300)
sdtadf = tabular.to_pandas_dataframe()
            

for cnt in df['WORK_ORDER_SRC_ID'].unique():
    tempdf = sdtadf[sdtadf['WORK_ORDER_NUMBER']==cnt]
    if len(tempdf)>0 :
        code = tempdf.loc[tempdf.index[0],'EXECUTION_CONDITION_CODE']
        ind = df[df['WORK_ORDER_SRC_ID'] == cnt].index
        df.loc[ind,'EXECUTION_CONDITION_CODE'] = code

opfilename = asset_name+ "_Backlog"
df.to_csv(opfilename+'.csv')
print(df.shape)

defdatastore = ws.get_default_datastore()
    # Register the dataset
ds = Dataset.Tabular.register_pandas_dataframe(dataframe=df, name=opfilename,       description=opfilename,target=defdatastore)

