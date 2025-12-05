# OnShape_Server_API (Temporarily)
Here is saved a website to test if my PYTHON API can comunicate with OnShapes Rest API via website, made with render.com.

**OnShape_API** folder conntains directories of the API, for easier viewing.

Link to access the server - https://onshape-server-api.onrender.com/  
The server can also start as soon as an iteration is performed, it can disconnect if there has been no activity for 15 minutes.

  
  Here will be a link to start the server remotely, if necessary and if the server did not start when the iteration is performed (Open server via link.) Link to open the server remotely   
  https://api.render.com/deploy/srv-d49ikkumcj7s73egu370?key=UL0PHK6ocok
  
  The rendering time depends greatly on the amount of data or imports or other information being read, the time can reach up to 1+ minutes, currently the approximate observed time is about _1 min to around 5 min, depending on what is new, and what has to be overrided (13.11.2025)_   
    
  (13.11.2025) Website is able to start correctly, make contact with the OnShape API to request authorization but cannot save token "_Token Exchange Failed
Status Code: 400_". Also it is able to check API working statuss. 

  (19.11.2025) Website is able to start corretly, make conctact with OnShape API, to request OAuth for authorization, Is able to save tokens that can be used for *1* Hours, is able to give access key, is able to fetch documents, is able to save, pull, and scan for ID's, Is able to save values in *JSON* or *CSV* file format, is able to get *BOM, Bounding Box, List of my documents, and get document elements*

  (20.11.2025) Error with javascript syntax, dosent allow me to press anybuttons. AT TIME Claude code version - 27v  
  (11:23PM)Clean and fixed version works a lot better, now allows to edit CSV or JSON file format, and save those values. Cannot access, bounding box, gives faulty *Get BOM* results using ID's.  
  (02.51PM) OnShape API with data base - began working on data base for OnShapes API, to save *keys* and *ID's* for every user that is using it, and as *primary key* using *emails* or custom *username* , made by a person itself, later for the coresponding *email* or *user* that *keys* and *ID's* will be used for OAuth and to authorize account for usage with *This api -> OnShapes Rest API* for comunnication or fetching files.  

  (21.11.2025) DataBase finished, now server can also pull data depending on the login user. Save ID's such as WorkSpace, Elemenet and Document. Push File back to OnShape - Currently unsusessful, can Log out, can choose what format BOM is - working 50/50, EVERYTHING else stays pretty much the same.  
  (02.45 PM) Recived new info about what to do, for server, where to add BOM overrwrite values. Created a new Issue in github - "Vai ir iespējams dabūt no configurācijām "Variable" kas ir iedvadīts deteļai kā garums, to kautkā ievilkt garuma property"".    
  (24.11.25) FOCUSING ON ADDING NEW FEATURES- using google gemini, tried to make feature script work, to later amplify it with the api, featurescript refuesed to work. Everything else seems to work correcrly, some errors for redircet in chromes google console.  
  (25.11.25) First time seeing an notify in console, that I can't acceses the OnShape to change values from HTML and API.  
  (26.11.25) Lots of errors, some were internal server errors, mistakes in code that prevented to sent values back, Mostly seen errors where 400 and 500, depending on the function. GET and POST erros were seen, while trying to get variables and while trying to push data back to OnShape.  
  (02:52) The errors, have not been fixed, notes of errors have been made, issues have been created. FS code and Idea has been scraped, waas not work the time. API holds ups nicely, one improvment could be made, ON CLICK, response time between click and result, current results are averaging around *1250ms*, ideal would be *100 - 500ms*.   
  (27.11.2025)
  (10:06AM) New notes of issues have been made in regards of using File:"Lenght_test". New time stamps of OnClick speed seen, some improvments in MIN speed - 938MS while max remains bigger 1295ms.  
  New files were added, for modifying and adding structure to the API and whole Server. For easier and faster working server.  
  Tried to change ReDircet URL's in OnShape dev portal, soo the API can Trust my source and allow me to acces part and assemblies, property values and edit them, also makde function for pushing values back working. The change didn't help fixing the issue, made the website blank. AT 11:41AM website is able to respond correctly. Login button isnt getting the right Redircet option (Possible mistake in OnShapes Dev portal). Gemini chat gave possible soulutions for a fix. First replaceble part didnt. Check and compared URL's everything seems to be correct, no typos seen.  
  I connected VsCode with my GitHub, for better coding and manegment, for further coding. Better and easeir to code and overview code, better to compare and update, edit it.   
  (12:05PM) Fixed the issue with login redirect. Still failed to get variables from config.  
  (02.28PM) Decied to try access data base, too see if any values get or dont get saved there. No luck currently using, DBeaver, while trying to run the data base in there, but there was an syntax errors. There is a possiblity, that I might not, be able to accces it, because of a PayWall by render.com. There is also a possiblity that it might work in VsCode. 
  (28.11.2025) I added another branch for the Main one, for code testing and I cleared out the Main one for the corrected and new code. Made notes for possible soulutions for problems with value Fetching/Pushing and Pulling, since its still not fixed.  
  (01:38PM) Tested and check if data based encrypton key is working correctly, both for DataBase and server access, it work great. Other suspition is that the PLAN for OnShape, that is being used - FREE PLAN, might limit what data or freatures does it allow to use. At the same time, sources say that it dosent impact anything. Watched youtube tutorails, for BOM and property meangemnt, there was nothing usefull, in regards for FS language, still unsuccesful, to make anything work in it, at the same time, there is no really reliable, sources for it and how to use it.   
  The code cant detect an objects Length, Wigth or Volume, e.t.c, even tho the code dosent make any errors, the surface is solid, element and part is not transparent, eveything for a normal of sucesseful detetion work proprely, but the API or even OnShapes API, just dosent seem to find or locate data. Idea is that the metadata is blocked, because, I cant even see those values in console while checking sources.   
  (02.12.2025) Transfered files succsesfully, with a lot if time, reactivated server and its online now. The only thing that is causing problems is that there is problems with Redirect from onshapes side.  
  (03.12.2025) Fixed errors with auth, now its possible to log in, changed the data base, soo it works and saves data diffrently. Now the main focus is on getting properties, pushing back BOM and created custom propteties. (03.32 PM) Most errors have been handled and some will be handled, curretly, all the excpectations for the WEB APP, have been made for the day, deffinetly, needs a lot more fixing. Deadline is tomoro, soo till tomoro this needs to be fixed. Deadline time is 4.DEC 01.00PM. Getting varibles, bounding box, and Getting/giving conifg, should be, made by tomorow and hopefully also finishing the job, by tomorow. Might have to ask Kalvis to send a nother copy, that has accses to inner resourses, soo test correctly, if the programm can see and update its metadata, or make the nesecarry functions, for it to work better, NOTE!!! The new copy, should close to NONE restrictions towards, getting and edting values, both from API side and from inner side of OnShape.  
  (04.12.2025) I will not make it till dead line which is today 04.12 at 01:00PM, soo it means, I have to atleast do most today, then give it to Kalvis and give him a task to test it, to see if it works better for ennterprise edition better, rather than free/student plan, that I have, since there might be some LIMITATIONS for it. If functions work out correctly, for enterprise edition, then, I can finish the solution.  
  (03.17PM) Made an idea, that due to a bit unbelivable values, its hard to belive, if they are made correcly, since, OnShape uses INCH as standart, but MiliMeters are needed, soo, I have to make a function, that checks, wheather or not, values are correct, using API comunication, I need to check, what values does, the PARTSTUDIO use, if inch, then convert to MILIMETERS. I need to increase, waiting times for gettinh the BOM, since some BOM documents in WORK spaces, are pretty large. After getting accses, hopefully tomorow, im gonna have to make tests, wheater or not "**CREATE LENGTH PROPERTIES**" Does create values correctly and if it even pushes them back to OnShape, also have to check wheater or not values get pushed back correctly back to OnShapes BOM.  
  (05.12.2025) Added a function that allows me to convert values to MM, currretly working with unrelieblity, but, that is a thing to fix.
    


               This page is created for a issue with OnShape seen in company named - Mechanika Engineering.  
               Created by an Intern at company - Aleks Ņikitins, Internship time by Valmieras Tehnikums from 27.10.2025 till 15.12.2025.  
               GitHub repository is owned by the creator - Aleks Ņikitins.
