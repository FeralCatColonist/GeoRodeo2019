import pandas as pd
print("Pandas at {pd.__version__}")
import numpy as np
print("Numpy at {np.version.full_version}")
import arcpy
print("ArcPy imported successfully.\n")
import datetime
import os
import shutil
import smtplib
import tempfile
import time
import traceback

def auto_truncate(val):
	'''this returns the first 255 characters of a string to play nicely with the file geodatabase string limit'''
	return val[:255]

def write_to_log(content):
	'''A simple log using a .txt'''
	log_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	with open(r"C:\Users\jcarmona\Desktop\__Production_Scripts\CIP_GoogleSheet_log.txt", "a") as log_file:
		log_file.write("\n{0} --- {1}".format(log_time, content))

def write_to_email(content, subject):
	'''This is an email process that takes one argument, the body of the message'''
	SERVER = SERVERNAME
	FROM = "AutoNotifer@mckinneytexas.org"
	TO = ["jcarmona@mckinneytexas.org"]
	SUBJECT = f"CIP to Google Sheet ALERT - {subject}"
	join_TO = ", ".join(TO)
	message = f"From: {FROM} \r\nTo: {join_TO} \r\nSubject: {SUBJECT} \r\n\n{content}"
	server = smtplib.SMTP(SERVER)
	server.login("AutoNotifier", password)
	server.sendmail(FROM, TO, message)
	server.quit()
	print("Done")
	
def CreateSDE_Version():
	'''This is to make sure that the version exists before the script runs'''
	print("Checking SDE connections.\n")
	sdeTempPath = tempfile.mkdtemp()
	arcpy.CreateDatabaseConnection_management(sdeTempPath, "Editor.sde", "SQL_SERVER", SERVERNAME, "OPERATING_SYSTEM_AUTH")
	sdeVersionNameFULL = ""
	sdeVersionLIST = []
	for version in arcpy.da.ListVersions(sdeTempPath + os.sep + "Editor.sde"):
		sdeVersionNameFULL = version.name.split(".")[0]        
		sdeVersionLIST.append(sdeVersionNameFULL)
		if sdeVersionNameFULL == '"MCKINNEY\\JCARMONA"':
			if version.description == "":
				arcpy.AlterVersion_management(sdeTempPath + os.sep + "Editor.sde", '"MCKINNEY\JCARMONA".CARMONA', description = "jcarmona@mckinneytexas.org | ext 7422")
		#print(sdeVersionLIST)
	if '"MCKINNEY\\JCARMONA"' not in sdeVersionLIST:
		print("\tCARMONA version not found, creating now.")
		arcpy.CreateVersion_management(sdeTempPath + os.sep + "Editor.sde", "sde.DEFAULT" ,"CARMONA", "PUBLIC")
		arcpy.AlterVersion_management(sdeTempPath + os.sep + "Editor.sde", '"MCKINNEY\JCARMONA".CARMONA', description = "jcarmona@mckinneytexas.org | ext 7422")
		print("Version created.")
	shutil.rmtree(sdeTempPath)

try: 
	CreateSDE_Version()
except Exception as e:
	write_to_log(f"There was an error: \n{traceback.format_exc()}")
	write_to_email(f"There was an error: \n{traceback.format_exc()}", "SDE Login Failed")

starttime = time.time()

tryagain = 0
while tryagain < 5:
	try:
		tryagain += 1
		#this is the standard way of making a Google Sheet a link-downloadable CSV after the unique key type: /export?format=csv
		CIP_sheet = "https://docs.google.com/spreadsheets/d/UNIQUEKEY/export?format=csv"
		df_checkcurrent = pd.read_csv(CIP_sheet)
		df_checkprevious = pd.read_csv(r"C:\Users\jcarmona\Desktop\__Production_Scripts\CIP_GoogleSheet.csv")
		if df_checkcurrent.equals(df_checkprevious):
			write_to_log("CIP Google Sheet has no changes to report")
			print("CIP Sheet is up to date, exiting.")
			exit()

		print("Reading and cleaning CIP Google Sheet.")
		df = pd.read_csv(CIP_sheet, converters ={'Project Description': auto_truncate, 'Project Notes': auto_truncate}) #read_csv can ingest a csv from a web link
		df_previous = pd.read_csv(r"C:\Users\jcarmona\Desktop\__Production_Scripts\CIP_GoogleSheet.csv")

		df['Project Funding'] = df['Project Funding'].replace('[\$,]', '', regex=True).astype(float) #clean the $s and ,s from the string budget field
		df['Project Start Date'] = df['Project Start Date'].replace('[TBD]', '', regex=True).astype(str) #clean TBD values from start date
		df['Estimated Project Completion Date'] = df['Estimated Project Completion Date'].replace('[TBD]', '', regex=True).astype(str) #clean TBD values from complete date
		df['Project Type'] = df['Project Type'].astype(str).str.upper()

		#check to see if GoogleSheet transferred correctly, if 'nan' values found, restart
		#this is probably a side-effect of the pandas read_csv() request happening too quickly
		#this is the reason this whole section is wrapped in a tryagain function
		list_nan = df['Project Start Date'].values
		if list_nan[0] == "nan":
			raise Exception("'nan' values found.")
		continue

	except Exception as e:
		print(f"\n{'-'*60} \n")
		print(traceback.format_exc())
		write_to_log(traceback.format_exc())
		write_to_log(f"Retrying execution, attempt: {tryagain}")
		print(f"Retrying execution in 5 seconds, attempt: {tryagain}")
		time.sleep(5)
		print(f"\n{'-'*60} \n")
		if tryagain == 5:
			write_to_email(f"There was a major error in the script, 5 tries exceeded: \n\n {traceback.format_exc()}", "pd.Read_CSV() failed!")
			exit()
		continue

try:
	input_array = np.array(np.rec.fromrecords(df.values)) #create numpy array from pandas dataframe
	col_names = df.dtypes.index.tolist() #grab column names from pandas dataframe as a list
	input_array.dtype.names = tuple(col_names) #set column names in numpy array   

	#googletable = r'%scratchGDB%\CIP_Google_Sheet_Table'
	googletable = r'in_memory\CIP_Google_Sheet_Table'

	#check needed if writing to physical location or loop continues past 1st iteration
	if arcpy.Exists(googletable):
		print("Previous CIP Google Sheet Table found. Deleting now.")
		arcpy.Delete_management(googletable)
	arcpy.da.NumPyArrayToTable(input_array, googletable)
	print("Converting CIP Google Sheet from CSV to Table in memory.")
	print("Adding new fields to CIP Google Sheet Table.")

	arcpy.AddField_management(googletable, "StartDate", "DATE")
	arcpy.AddField_management(googletable, "CompleteDate", "DATE")
	arcpy.AddField_management(googletable, "GeneralStatus", "TEXT", field_length=50)

	#this next section handles putting the string dates into a date field using calculate field with a codeblock
	#the codeblock handles the '' by telling it to skip, each '' record prevents a straight transfer
	print("Calculating new date fields in CIP Google Sheet Table.")
	codeblock01 = """def makeathing(field):
		if field != '':
			return field
		else:
			return"""       
	arcpy.CalculateField_management(googletable, "StartDate", "makeathing(!Project_Start_Date!)", "PYTHON3", codeblock01)
	arcpy.CalculateField_management(googletable, "CompleteDate", "makeathing(!Estimated_Project_Completion_Date!)", "PYTHON3", codeblock01)

	print("Calculating general status field in CIP Google Sheet Table.")
	codeblock02 = """def test_general_status(field):
		if field in ["PLANNING", "PLANNED IMPROVEMENT"]:
			return "PLANNED IMPROVEMENT"
		elif field in ["DESIGN", "BIDDING", "LAND ACQUISITION", "FRANCHISE RELOCATION"]:
			return "DESIGN"
		elif field == "CONSTRUCTION":
			return "CONSTRUCTION"
		elif field == "COMPLETE":
			return "COMPLETE"
		else:
			return"""
	arcpy.CalculateField_management(googletable, "GeneralStatus", "test_general_status(!Project_Status!)", "PYTHON3", codeblock02)

	print("\nConnecting to the SDE and appropriate version.")
	sdeTempPath = tempfile.mkdtemp()
	arcpy.CreateDatabaseConnection_management(sdeTempPath, "Editor.sde", "SQL_SERVER", SERVERNAME, "OPERATING_SYSTEM_AUTH")
	arcpy.CreateDatabaseConnection_management(sdeTempPath, "CARMONA.sde", "SQL_SERVER", SERVERNAME, "OPERATING_SYSTEM_AUTH", version = '"MCKINNEY\JCARMONA".CARMONA')

	EditSDE = os.path.join(sdeTempPath, "Editor.sde")
	EditSDE_Carmona = os.path.join(sdeTempPath, "CARMONA.sde")
	sde_CIP1923 = os.path.join(EditSDE_Carmona, "SDE.SDE.CIPs", "SDE.SDE.CIP1923")
	sde_CIPFY1923 = os.path.join(EditSDE_Carmona, "SDE.SDE.CIPs", "SDE.SDE.CIPFY1923")
	sde_CIP1923_Point = os.path.join(EditSDE_Carmona, "SDE.SDE.CIPs", "SDE.SDE.CIP1923_Point")

	#This is a test to check if there are new records in the Google Sheet that have yet to be added to the SDE
	#First the dataframe column ['Project No'] is sent to list; then a da.SearchCursor to iterate through records
	#and append them to another list. The googleprojects list is compared against the sde list
	#all positives are sent to the email alert function
	list_googleprojects = df['Project No'].tolist()
	list_sde = []
	list_email = []
	print("\nChecking CIP Google Sheet Table for new projects.")
	with arcpy.da.SearchCursor(sde_CIP1923, "CIPProjectNumber") as scursor:
		for srow in scursor:
			list_sde.append(srow[0])
	for item in list_googleprojects:
		if item not in list_sde:
			list_email.append(item)
	if not list_email:
		print("\tNo new projects were found.")
	else:
		print("\tThe following projects are new: {}".format(list_email))
		write_to_log("The following projects are new: {}".format(list_email))
		write_to_email(f"Manual work is needed! \n\nThe following projects are new: {list_email}", "New Projects need to be drawn!")

	updatefields_google = ["Project_No", "Project_Name", "Project_Funding", "Project_Description", "Project_Status", "GeneralStatus", "StartDate", "CompleteDate", "Project_Type", "Project_Notes"]
	updatefields_sde = ["CIPProjectNumber", "ProjectName", "ProjectBudget", "ProjectDescription", "ProjectStatus", "GeneralStatus", "StartDate", "CompleteDate", "ProjectType", "ProjectNotes", "ProjectUpdated"]
	counter = 1

	arcpy.env.workspace = EditSDE_Carmona
	edit = arcpy.da.Editor(EditSDE_Carmona)

	print("\nInitiating editing loops for all records:")
	edit.startEditing(True, True)
	with arcpy.da.SearchCursor(googletable, updatefields_google) as scursor:
		for srow in scursor:
			update_query = "CIPProjectNumber = '" + srow[0] + "'"
			print(f"\tCIP Project {srow[0]}, {counter-1} edits pending")
			ucursor = arcpy.da.UpdateCursor(sde_CIP1923, updatefields_sde, update_query)
			edit.startOperation()
			for urow in ucursor:
				urow[1] = srow[1]
				urow[2] = srow[2]
				urow[3] = srow[3]
				urow[4] = srow[4]
				urow[6] = srow[6]
				urow[7] = srow[7]
				#check if these 2 fields have new attributes
				#if so, we'll update a field urow[10] that logs new things
				#this new field powers a symbology alert in our webmap
				#then overwrite the fields with the new values
				if (
					urow[9] != srow[9] or
					urow[5] != srow[5]
				):
					urow[10] = datetime.date.today()
				urow[5] = srow[5]
				urow[9] = srow[9]
				ucursor.updateRow(urow)
				counter += 1
			edit.stopOperation()

			ucursor = arcpy.da.UpdateCursor(sde_CIPFY1923, updatefields_sde, update_query)
			edit.startOperation()
			for urow in ucursor:
				urow[1] = srow[1]
				urow[2] = srow[2]
				urow[3] = srow[3]
				urow[4] = srow[4]
				urow[6] = srow[6]
				urow[7] = srow[7]
				if (
					urow[9] != srow[9] or
					urow[5] != srow[5]
				):
					urow[10] = datetime.date.today()
				urow[5] = srow[5]
				urow[9] = srow[9]
				ucursor.updateRow(urow)
				counter += 1
			edit.stopOperation()

			ucursor = arcpy.da.UpdateCursor(sde_CIP1923_Point, updatefields_sde, update_query)
			edit.startOperation()
			for urow in ucursor:
				urow[1] = srow[1]
				urow[2] = srow[2]
				urow[3] = srow[3]
				urow[4] = srow[4]
				urow[6] = srow[6]
				urow[7] = srow[7]
				if (
					urow[9] != srow[9] or
					urow[5] != srow[5]
				):
					urow[10] = datetime.date.today()
				urow[5] = srow[5]
				urow[9] = srow[9]
				ucursor.updateRow(urow)
				counter += 1
			edit.stopOperation()
	
	print(\n"Editing loops complete for CIP layers.")
	print(f"Editing environment active: {edit.isEditing}")
	edit.stopEditing(True)
	print("Edits saved.")
	print(f"Editing environment active: {edit.isEditing}")
	arcpy.ReconcileVersions_management(EditSDE, "ALL_VERSIONS", "sde.DEFAULT", r'"MCKINNEY\JCARMONA".CARMONA', "LOCK_ACQUIRED", 
								"NO_ABORT", "BY_OBJECT", "FAVOR_TARGET_VERSION", "POST", "KEEP_VERSION", None, "PROCEED")
	print("Version has reconciled and posted to Default.")
	write_to_log("Script ran successfully")

	#setting index to false in the CSV will make it exactly match an unaltered dataframe
	#this allows us to check the dataframe against the CSV at next runtime
	df_checkcurrent.to_csv(r"C:\Users\jcarmona\Desktop\__Production_Scripts\CIP_GoogleSheet.csv", index=False)
	print("CIP Google Sheet updates have been written to CSV for future checks.")
	write_to_log("CIP Google Sheet updates have been written to CSV for future checks.")

except Exception as e:
	print(f"\n{'-'*60}\n")
	print("Things did not go as planned...\n") 
	print(traceback.format_exc())
	write_to_log(traceback.format_exc())
	print("Error logged.")
	print(f"\n{'-'*60}\n")
	write_to_email(f"There was a major error in the script, check your logs: \n\n {traceback.format_exc()}", "Error in Main Script")

shutil.rmtree(sdeTempPath)
endtime = time.time() - starttime
print(f"This process took {round(endtime,2)} seconds")
write_to_log(f"This process took {round(endtime,2)} seconds")