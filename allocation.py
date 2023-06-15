import pandas as pd
import numpy as np



def perform_allocation(tempdf,FCdf,weeknumber,capacitydf):
    
    FCdf.loc[tempdf.index,'Allocated'] = 0
    FCdf.loc[tempdf.index,'AlternateESD'] = weeknumber
    # Reduce the capacity
    for gg in tempdf['UpdatedWorkCenter'].unique():
        
        FCdf.loc[tempdf[tempdf['UpdatedWorkCenter'] == gg].index,'AllocatedReason'] = 'Available Capacity for this WorkCenter in the Week :' + str(weeknumber) + ': '+ str(capacitydf.loc[weeknumber,gg]) +',Required Capacity for this WorkCenter in the Week :' +str(weeknumber) + ' : '+ str(tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum()) + '. LAFD Constraint Satisified. Bundling of WO Satsified'
        capacitydf.loc[weeknumber,gg] = capacitydf.loc[weeknumber,gg] - tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum()
         
        
    return FCdf,capacitydf
            
def iscapacityavailableforWO(capacitydf,tempdf,weeknumber):

    doable = 0
    for gg in tempdf['UpdatedWorkCenter'].unique():
#         print(weeknumber,gg,tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum(),capacitydf.loc[weeknumber,gg])
        if tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum() <= capacitydf.loc[weeknumber,gg] :
            doable = doable + 1           
        else:
            return False
    if doable > 0 :
        return True
    else:
        return False
        
def reasonfornotfilling(tempdf,FCdf,weeknumber,capacitydf):
    for gg in tempdf['UpdatedWorkCenter'].unique():
        FCdf.loc[tempdf[tempdf['UpdatedWorkCenter'] == gg].index,'MoveReason'] = FCdf.loc[tempdf[tempdf['UpdatedWorkCenter'] == gg].index,'MoveReason'] + 'Available Capacity in Week ' +str(weeknumber) +': ' +str(capacitydf.loc[weeknumber,gg]) +',Required Capacity in Week '+str(weeknumber) + ':' + str(tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum())
        FCdf.loc[tempdf[tempdf['UpdatedWorkCenter'] == gg].index,'Capreqd'] = str(tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum())
        
    return FCdf


def updatevalidation_matrix_before(validation_matrix,tempdf,capdf,weekno,linenumber):


    for gg in tempdf['UpdatedWorkCenter'].unique():
        validation_matrix.loc[linenumber,'Week'] = weekno
        validation_matrix.loc[linenumber,'WO'] = tempdf['Order'].unique()[0]
        validation_matrix.loc[linenumber,'WorkCraft'] = gg
        validation_matrix.loc[linenumber,'RequiredCapacity'] = tempdf[tempdf['UpdatedWorkCenter'] == gg]['Work'].sum()
        validation_matrix.loc[linenumber,'AvailableCapacity'] = capdf.loc[weekno,gg]
        validation_matrix.loc[linenumber,'PriorityWO'] =  tempdf.loc[tempdf.index[0],'Priority']
        validation_matrix.loc[linenumber,'ESD_WeekNumber'] = tempdf.loc[tempdf.index[0],'ESD_WeekNumber']
        validation_matrix.loc[linenumber,'LAFD_WeekNumber'] = tempdf.loc[tempdf.index[0],'LAFD_WeekNumber']
        linenumber=linenumber+1
        
    
    return validation_matrix,linenumber

def updatevalidation_matrix_after(valdf,tempdf,capdf,weekno,linenumber,priorityfilling):
    
    for gg in tempdf['UpdatedWorkCenter'].unique():
        valdf.loc[linenumber,'AvailableCapacity_afterallocation'] = capdf.loc[weekno,gg]
        valdf.loc[linenumber,'priorityfilling'] = priorityfilling   
        linenumber=linenumber+1
        


    return valdf
          
    
    
def allocation_of_cm(df,capacitydf, total_weeks):
    # Seggregating CM versus the rest stagnant order types

    FCdf = df[df['Order Type'] == '72FC']
    FPdf = df[ ((df['Order Type'] == '72FP') | (df['Order Type'] == 'GEN') | (df['Order Type'] == 'ZADM')| (df['Order Type'] == '71PO'))]
    FPdf['Allocated']=0


    validation_matrix = pd.DataFrame(columns=['Week','WO','WorkCraft','RequiredCapacity','AvailableCapacity','AvailableCapacity_afterallocation','priorityfilling','ESD_WeekNumber','LAFD_WeekNumber'])
    uplineno=0


    for cnt in range(0,total_weeks):
    #     print(cnt)
        k=1
        refdf = FCdf[ (FCdf['ESD_WeekNumber'] <= cnt) & (FCdf['LAFD_WeekNumber'] >= cnt)]
        refdf = refdf[refdf['Allocated']==1]
        refdf = refdf[ (refdf['ESD_WeekNumber']) <= (refdf['LAFD_WeekNumber'])]
        refdf= refdf.sort_values(by = ['Priority','LAFD_WeekNumber','Work'], ascending=[True,True,True])

        for count in refdf['Order'].unique():    
            iscapacityavailable = iscapacityavailableforWO(capacitydf,refdf[refdf['Order']==count],cnt) 
            
            lineno = uplineno
            validation_matrix,uplineno = updatevalidation_matrix_before(validation_matrix,refdf[refdf['Order']==count],capacitydf,cnt,uplineno)
            
            if  iscapacityavailable == True:
                curr_wo = refdf[refdf['Order']==count]
                FCdf,capacitydf = perform_allocation(curr_wo,FCdf,cnt,capacitydf)
                FCdf.loc[curr_wo.index,'PriorityFilling'] = k
                
                validation_matrix = updatevalidation_matrix_after(validation_matrix,refdf[refdf['Order']==count],capacitydf,cnt,lineno,k)
                
                k=k+1
            else:
                curr_wo = refdf[refdf['Order']==count]
                FCdf =  reasonfornotfilling(curr_wo,FCdf,cnt,capacitydf)


    # Reason for Unallocated Status
    unallocdf = FCdf[FCdf['Allocated']==1]

    # FCdf.loc[FCdf['ESD_WeekNumber'].isnull().index,'UnAllocatedReason'] = ' LAFD lesser than ESD. This item is Unscheduled'
    # FCdf.loc[FCdf['LAFD_WeekNumber'].isnull().index,'UnAllocatedReason'] = ' LAFD lesser than ESD. This item is Unscheduled'

    FCdf.loc[unallocdf.index,'UnAllocatedReason'] = ' WO Bundling with the available capacity not Possible within LAFD. This item is Unscheduled'
    ind = unallocdf[unallocdf['ESD_WeekNumber'] > unallocdf['LAFD_WeekNumber']].index
    FCdf.loc[ind,'UnAllocatedReason'] = ' LAFD lesser than ESD. This item is Unscheduled'
    # ind = unallocdf[unallocdf['MoveReason'] != ''].index

    return FCdf,validation_matrix,FPdf,unallocdf,capacitydf
