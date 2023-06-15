import pandas as pd
import azureml.core
from azureml.core import Workspace, Dataset, Environment, Datastore
from azureml.core import Run


 # Load the workspace from the saved config file
ws = Workspace.get(name="eunmldevamlwsgom2",subscription_id='cf11c61d-e6ca-4f6b-b8df-d2a77e8a4d04',           resource_group='SEQ00963-NPRD-EUN-MLDEV-AML-gom2')
print('Ready to use Azure ML {} to work with {}'.format(azureml.core.VERSION, ws.name))
run = Run.get_context()


def modify_capacity_matrix(tempdf,assetname):
    if assetname=='URSA':
        arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Ursa Utilities Crane Mechanic','Ursa Utilities Solar Mechanic','Ursa Bilfinger Maintenance Crew']

    if assetname == 'Olympus':
        arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Crane Mechanic','Turbine Mechanic','Olympus Bilfinger Maintenance Crew']

    if assetname == 'Auger':
        arr = ['ACR/Instrument Technician','Electrician','Mechanic','ET/CAO','Crane Mechanic','Auger Solar Mechanic','Auger Bilfinger Maintenance Crew']
    
    modified_df = pd.DataFrame(index=tempdf.Week)
    flag=0
    for cnt in arr:
        for count in tempdf.Week:
            k = count + (flag*max(tempdf.Week))
            modified_df.loc[k,'Asset'] = assetname
            modified_df.loc[k,'UpdatedWorkCenter'] = cnt
            modified_df.loc[k,'Week'] = count
            row = tempdf[tempdf['Week']==count].index[0]
            modified_df.loc[k,'TotalCapacity'] = tempdf.loc[row,cnt]
            modified_df.loc[k,'Limit'] = tempdf.loc[row,cnt+'_Limit']
            # modified_df.loc[k,'ReqdCapacityBefore'] = tempdf.loc[row,cnt+'_Capacity_Reqd_CM_Before']
            # modified_df.loc[k,'ReqdCapacityAfter'] = tempdf.loc[row,cnt+'_Capacity_Reqd_CM_After']

            modified_df.loc[k,'TotalRequirement'] = tempdf.loc[row,cnt+'_TotalRequirement']
            modified_df.loc[k,'CMRequirement'] = tempdf.loc[row,cnt+'_CMRequirement']

            modified_df.loc[k,'Executable_WithoutMove_AfterOptimization'] = tempdf.loc[row,cnt+'_Executable_WithoutMove_AfterOptimization']
            modified_df.loc[k,'Executable_WithMove_AfterOptimization'] = tempdf.loc[row,cnt+'_Executable_WithMove_AfterOptimization']
            modified_df.loc[k,'NonExecutable_AfterOptimization'] = tempdf.loc[row,cnt+'_NonExecutable_AfterOptimization']



        flag = flag+1
    return modified_df

# After Optimizatin Merge

dataset1 = Dataset.get_by_name(ws, name='URSA_AfterOptimization')
dataset2 = Dataset.get_by_name(ws, name='Olympus_AfterOptimization')
dataset3 = Dataset.get_by_name(ws, name='Auger_AfterOptimization')
dataset1 = dataset1.to_pandas_dataframe()
dataset2 = dataset2.to_pandas_dataframe()
dataset3 = dataset3.to_pandas_dataframe()
merged = pd.concat([dataset1,dataset2,dataset3],axis=0,ignore_index=True)

defdatastore = ws.get_default_datastore()
# Register the dataset
ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=merged, 
        name='After_Optimization', 
        description='After_Optimization',
        target=defdatastore
    )


# Capacity merge Merge


dataset1 = Dataset.get_by_name(ws, name='URSA_CapacityMatrix')
dataset2 = Dataset.get_by_name(ws, name='Olympus_CapacityMatrix')
dataset3 = Dataset.get_by_name(ws, name='Auger_CapacityMatrix')

dataset1 = dataset1.to_pandas_dataframe()
# dataset1 = dataset1.add_prefix('URSA_')
dataset1 = modify_capacity_matrix(dataset1,'URSA')

dataset2 = dataset2.to_pandas_dataframe()
# dataset2 = dataset2.add_prefix('Olympus_')
dataset2 = modify_capacity_matrix(dataset2,'Olympus')

dataset3 = dataset3.to_pandas_dataframe()
# dataset3 = dataset3.add_prefix('Auger_')
dataset3 = modify_capacity_matrix(dataset3,'Auger')


merged = pd.concat([dataset1,dataset2,dataset3],axis=0,ignore_index=True)

defdatastore = ws.get_default_datastore()
# Register the dataset
ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=merged, 
        name='All_CapacityMatrix', 
        description='All_CapacityMatrix',
        target=defdatastore
    )



# ValidationMatrix Merge

dataset1 = Dataset.get_by_name(ws, name='URSA_ValidationMatrix')
dataset2 = Dataset.get_by_name(ws, name='Olympus_ValidationMatrix')
dataset3 = Dataset.get_by_name(ws, name='Auger_ValidationMatrix')
dataset1 = dataset1.to_pandas_dataframe()
dataset1['Asset'] = 'URSA'
dataset2 = dataset2.to_pandas_dataframe()
dataset2['Asset'] = 'Olympus'
dataset3 = dataset3.to_pandas_dataframe()
dataset3['Asset'] = 'Auger'
merged = pd.concat([dataset1,dataset2,dataset3],axis=0,ignore_index=True)

defdatastore = ws.get_default_datastore()
# Register the dataset
ds = Dataset.Tabular.register_pandas_dataframe( 
        dataframe=merged, 
        name='ValidationMatrix', 
        description='ValidationMatrix',
        target=defdatastore
    )
