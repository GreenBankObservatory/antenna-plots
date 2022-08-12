The Interactive Dashboard of Green Bank Telescope (GBT) Antenna Data provides an interface to visualize sky positions.

This project was conducted by a REU Summer Student at the Green Bank Observatory.

The motivation of this project was to give users a tool that can help visualize sky positions data taken by the GBT and to link these positions to more information about the observations. The dashboard allows users to filter the antenna data by date range, receiver, backend, or even by session. These filters help users fine-tune the observations that they want to look at.

The linking of antenna positions to more information in the dashboard was not completed. The project almost got to the point of almost being ready to link the points to an external source. The main functionality of this project is using the widgets to change what antenna positions are showns on the projections. This will be used to link the certain antenna positions to the archive in the future.  

The main notebook with the dashboard is three_interactive.ipynb, which uses the 300K dataset. main_interactive.ipynb is the same but it uses the 2M dataset. The rest of the notebooks were used to demostrate specific features of the dashboard or were used as building blocks for creating the main notebooks. 

The project was created using Python 3.9.0 and the following libraries:
Bokeh==2.4.3
Datashader==0.14.0
Geoviews==1.9.5
Holoview==1.14.9
Panel==0.13.0

