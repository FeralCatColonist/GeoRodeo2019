# GeoRodeo2019
Notebook &amp; Materials for Presentation on Bringing a Google Sheet into an Esri SDE

This presentation was given on a Jupyter Notebook running RISE JS:
https://rise.readthedocs.io/en/stable/
https://www.blog.pythonlibrary.org/2018/09/25/creating-presentations-with-jupyter-notebook/

Here's a copy of the Google Sheet dataset with read-only rights:
https://docs.google.com/spreadsheets/d/1QB1pZQ3CN45ZYS2sc4LnuoOaImL5lQsP-ObWNQW5FjY/edit#gid=0

This script was written before the Google Docs API came out, I would recommend using the Google Docs API instead as there are some unusual errors that crop up, like 'nan' values on the first pd.read_csv() call. That's handled in the production script using a "try again" method, but kind of a band-aid. The better way to do it, would be the right way:
https://developers.google.com/docs/api/

As a side note, you can also register a Google Sheet with ArcGIS Online:
https://doc.arcgis.com/en/arcgis-online/manage-data/add-items.htm

Another note, ArcPy will not work without an installation of ArcGIS Pro or ArcMap on your computer. You can clone the ArcGIS Pro path using conda either within Pro or using a standalone conda installation. Copy the arcgispropy3 folder into your Anaconda envs folder and poof! you can use ArcGIS with your Jupyter Notebook

Esri is also releasing ArcGIS Notebooks which is basically this. Available via Portal (at 10.7.1) or AGOL by the end of 2019. 
