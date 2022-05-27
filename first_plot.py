import numpy as np
import matplotlib.pyplot as plt

from astropy.io import fits
from astropy.table import Table
from astropy.coordinates import Angle
import astropy.units as u


tbl = fits.open("stack_table.fits")
antenna_data=Table(tbl[1].data)
tbl.close()

ra = Angle(antenna_data['RAJ2000']*u.degree)
ra = ra.wrap_at(180*u.degree)
dec = Angle(antenna_data['DECJ2000']*u.degree)


fig = plt.figure(figsize=(12,10))
ax = fig.add_subplot(111, projection="mollweide")
ax.scatter(ra.radian, dec.radian,marker="o", facecolor='Green',edgecolor='Black',linewidth=2, s=7, alpha=.08)
ax.set_xticklabels(['14h','16h','18h','20h','22h','0h','2h','4h','6h','8h','10h'])
ax.set_xlabel("RAJ2000")
ax.set_ylabel("DECJ2000")
ax.grid(True)
plt.title("GBT")

#fig.savefig("map4.png")
plt.show()

