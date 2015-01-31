#!/usr/bin/env python

#stdlib imports
import copy
import os.path

#third party imports
from mpl_toolkits.basemap import Basemap, shiftgrid, cm
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
from matplotlib import cm
import matplotlib as mpl

#local imports
from neicio.gmt import GMTGrid
from neicutil.text import ceilToNearest,floorToNearest,roundToNearest

ALPHA = 0.7
AZDEFAULT=90
ALTDEFAULT=20

def getGridExtent(grid,basemap):
    lonmin,lonmax,latmin,latmax = grid.getRange()
    xmin,ymin = basemap(lonmin,latmin)
    xmax,ymax = basemap(lonmax,latmax)
    extent = (xmin,xmax,ymin,ymax)
    return extent

def getTopoRGB(topogrid):
    topodat = topogrid.getData().copy()
    cy = topogrid.geodict['ymin'] + (topogrid.geodict['ymax'] - topogrid.geodict['ymin'])/2.0
    #flag the regions where topography is less than 0 (we'll color this ocean later)
    i = np.where(topodat < 0)

    #do shaded relief stuff
    #keys are latitude values
    #values are multiplication factor
    zdict = {0:0.00000898,
             10:0.00000912,
             20:0.00000956,
             30:0.00001036,
             40:0.00001171,
             50:0.00001395,
             60:0.00001792,
             70:0.00002619,
             80:0.00005156}
    #find the mean latitude of the map we're making, and use that to come up with a zfactor
    mlat = abs(int(round(cy/10)*10))
    zfactor = zdict[mlat]
    ls = LightSource(azdeg = AZDEFAULT, altdeg = ALTDEFAULT)

    #draw the ocean in light blue
    water_color = [.47,.60,.81]
    palette1 = copy.deepcopy(cm.binary)
        
    #draw the light shaded-topography
    rgbdata = topodat*zfactor #apply the latitude specific zfactor correction
    rgb = ls.shade(rgbdata,cmap=palette1) #apply the light shading to our corrected topography

    #this is an rgb data set now, so masking the pixels won't work, but explicitly setting all of the
    #"bad" pixels to our water color will
    red = rgb[:,:,0]
    green = rgb[:,:,1]
    blue = rgb[:,:,2]
    red[i] = water_color[0]
    green[i] = water_color[1]
    blue[i] = water_color[2]
    rgb[:,:,0] =  red
    rgb[:,:,1] =  green
    rgb[:,:,2] =  blue

    rgb = np.flipud(rgb)

    return (rgb,palette1)

def getMapLines(dmin,dmax):
    NLINES = 4
    drange = dmax-dmin
    if drange > 4:
        near = 1
    else:
        if drange >= 0.5:
            near = 0.25
        else:
            near = 0.125
    inc = roundToNearest(drange/NLINES,near)
    if inc == 0:
        near = np.power(10,round(math.log10(drange))) #make the increment the closest power of 10
        inc = ceilToNearest(drange/NLINES,near)
        newdmin = floorToNearest(dmin,near)
        newdmax = ceilToNearest(dmax,near)
    else:
        newdmin = ceilToNearest(dmin,near)
        newdmax = floorToNearest(dmax,near)
    darray = np.arange(newdmin,newdmax+inc,inc)
    if darray[-1] > dmax:
        darray = darray[0:-1]
    return darray

def latstr(parallel):
    if parallel < 0:
        parstr = '%.2f' % (-1*parallel) + '$\degree$ S'
    else:
        parstr = '%.2f' % (parallel) + '$\degree$ N'
    return parstr

def lonstr(meridian):
    if meridian < 0:
        merstr = '%.2f' % (-1*meridian) + '$\degree$ W'
    else:
        merstr = '%.2f' % (meridian) + '$\degree$ E'
    return merstr

def getMapTicks(m,xmin,xmax,ymin,ymax):
    meridians = getMapLines(xmin,xmax)
    parallels = getMapLines(ymin,ymax)
    #do tick stuff
    xlabels = [lonstr(mer) for mer in meridians]
    ylabels = [latstr(par) for par in parallels]
    xticks = []
    yticks = []
    for i in range(0,len(meridians)):
        lat = ymin
        lon = meridians[i]
        x,y = m(lon,lat)
        xticks.append(x)
    for i in range(0,len(parallels)):
        lon = xmin
        lat = parallels[i]
        x,y = m(lon,lat)
        yticks.append(y)
    
    return (xticks,xlabels,yticks,ylabels)
    

def makeDualMap(lqgrid,lsgrid,topogrid,slopegrid,eventdict,outfolder,isScenario=False):
    # create the figure and axes instances.
    fig = plt.figure()
    ax = fig.add_axes([0.1,0.1,0.8,0.8])
    # setup of basemap ('lcc' = lambert conformal conic).
    # use major and minor sphere radii from WGS84 ellipsoid.
    xmin,xmax,ymin,ymax = topogrid.getRange()
    clat = ymin + (ymax-ymin)/2.0
    clon = xmin + (xmax-xmin)/2.0
    m = Basemap(llcrnrlon=xmin,llcrnrlat=ymin,urcrnrlon=xmax,urcrnrlat=ymax,\
                rsphere=(6378137.00,6356752.3142),\
                resolution='l',area_thresh=1000.,projection='lcc',\
                lat_1=clat,lon_0=clon,ax=ax)
    
    rgb,topopalette = getTopoRGB(topogrid)
    topogrid2 = GMTGrid()
    topogrid2.loadFromGrid(topogrid)
    topogrid2.interpolateToGrid(lqgrid.geodict)

    
    iwater = np.where(topogrid2.griddata < 0) 
    im = m.imshow(rgb,cmap=topopalette)

    #this business apparently has to happen after something has been 
    #rendered on the map, which I guess makes sense.
    #draw the map ticks on outside of all edges
    fig.canvas.draw() #have to do this for tick stuff to show
    xticks,xlabels,yticks,ylabels = getMapTicks(m,xmin,xmax,ymin,ymax)
    plt.sca(ax)
    plt.tick_params(axis='both',direction='in',right='on',colors='white')
    plt.xticks(xticks,xlabels,size=6)
    plt.yticks(yticks,ylabels,size=6)
    for tick in ax.axes.yaxis.get_major_ticks():
        tick.set_pad(-33)
        tick.label2.set_horizontalalignment('right')
    for tick in ax.axes.xaxis.get_major_ticks():
        tick.set_pad(-10)
        tick.label2.set_verticalalignment('top')
    [i.set_color("white") for i in plt.gca().get_xticklabels()]
    [i.set_color("white") for i in plt.gca().get_yticklabels()]
    #ax.axis[:].invert_ticklabel_direction()
    
    
    #render liquefaction
    lqdat = lqgrid.getData().copy() * 100.0
    clear_color = [0,0,0,0.0]
    palettelq = cm.autumn_r
    i = np.where(lqdat < 2.0)
    lqdat[i] = 0
    lqdat[iwater] = 0
    lqdatm = np.ma.masked_equal(lqdat, 0)
    palettelq.set_bad(clear_color,alpha=0.0)
    extent = getGridExtent(lqgrid,m)
    lqprobhandle = m.imshow(lqdatm,cmap=palettelq,vmin=2.0,vmax=20.0,alpha=ALPHA,origin='upper',extent=extent)
    # ax2 = fig.add_axes([0.85,0.1,0.05,1.0])
    # plt.sca(ax2)
    m.colorbar(mappable=lqprobhandle)

    #render landslide
    lsdat = lsgrid.getData().copy() * 100.0
    clear_color = [0,0,0,0.0]
    palettels = cm.cool
    i = np.where(lsdat < 2.0)
    lsdat[i] = 0
    lsdat[iwater] = 0
    lsdatm = np.ma.masked_equal(lsdat, 0)
    palettels.set_bad(clear_color,alpha=0.0)
    extent = getGridExtent(lsgrid,m)
    lsprobhandle = plt.imshow(lsdatm,cmap=palettels,vmin=2.0,vmax=20.0,alpha=ALPHA,origin='upper',extent=extent)

    #draw landslide colorbar on the left side
    axleft = fig.add_axes([0.133,0.1,0.033,0.8])
    norm = mpl.colors.Normalize(vmin=2.0,vmax=20.0)
    cb1 = mpl.colorbar.ColorbarBase(axleft, cmap=palettels,norm=norm,orientation='vertical')
    cb1.ax.yaxis.set_ticks_position('left')

    #draw titles
    cbartitle_ls = 'Landslide\nProbability'
    plt.text(-1.0,1.03,cbartitle_ls,multialignment='left',axes=ax)

    cbartitle_ls = 'Liquefaction\nProbability'
    plt.text(20.0,1.03,cbartitle_ls,multialignment='left',axes=ax)

    axwidth = 20 #where can I get this from?

    #draw a map boundary, fill in oceans with water
    water_color = [.47,.60,.81]
    m.drawmapboundary(fill_color=water_color)

    #draw coastlines
    #m.drawcoastlines()

    if isScenario:
        title = eventdict['loc']
    else:
        timestr = eventdict['time'].strftime('%b %d %Y')
        title = 'M%.1f %s\n %s' % (eventdict['mag'],timestr,eventdict['loc'])

    #draw the title on the plot
    ax.set_title(title)
    
    #draw scenario watermark, if scenario
    if isScenario:
        plt.sca(ax)
        cx,cy = m(clon,clat)
        plt.text(cx,cy,'SCENARIO',rotation=45,alpha=0.10,size=72,ha='center',va='center',color='red')
    
    #plt.title(ptitle,axes=ax)
    outfile = os.path.join(outfolder,'%s.pdf' % eventdict['eventid'])
    plt.savefig(outfile)
    print 'Saving map output to %s' % outfile

if __name__ == '__main__':
    pass
