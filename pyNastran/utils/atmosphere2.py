"""
Contains the following atmospheric functions:

 - density = atm_density(alt, mach)
 - mach = atm_mach(alt, velocity)
 - velocity = atm_velocity(alt, mach)
 - pressure = atm_pressure(alt)
 - temperature = atm_temperature(alt)
 - sos = atm_speed_of_sound(alt)
 - mu = atm_dynamic_viscosity_mu(alt)
 - nu = atm_kinematic_viscosity_nu(alt)
 - eas = atm_equivalent_airspeed(alt, mach)

All the default units are in English units because the source equations
are in English units.
"""
from __future__ import print_function
import sys
from math import log, exp
import numpy as np

def _update_alt(alt, alt_units):
    """
    Converts altitude alt_units to feet

    Parameters
    ----------
    alt : float
        altitude in feet or meters
    alt_units : str; default='ft'
        sets the units for altitude; ft, m, kft

    Returns
    -------
    alt2 : float
        altitude in feet
    """
    if alt_units == 'ft':
        factor = 1.
    elif alt_units == 'm':
        factor = 1. / 0.3048
    elif alt_units == 'kft':
        factor = 1000.
    else:
        raise RuntimeError('alt_units=%r is not valid; use [ft, m, kft]' % alt_units)
    alt2 = alt * factor
    return alt2


def get_alt_for_density(density):
    """
    Gets the altitude associated with a given air density.

    Parameters
    ----------
    density : float
        the air density in slug/ft^3

    Returns
    -------
    alt : float
        the altitude in feet
    """
    dalt = 500.
    alt_old = 0.
    alt_final = 5000.
    n = 0
    tol = 5. # ft

    # Newton's method
    while abs(alt_final - alt_old) > tol and n < 20:
        alt_old = alt_final
        alt1 = alt_old
        alt2 = alt_old + dalt
        rho1 = atm_density(alt1)
        rho2 = atm_density(alt2)
        m = dalt / (rho2 - rho1)
        alt_final = m * (density - rho1) + alt1
        n += 1
    if n > 18:
        print('n = %s' % n)
    return alt_final


def get_alt_for_eas_mach(equivalent_airspeed, mach, velocity_units='ft/s', alt_units='ft'):
    """
    Gets the altitude associated with a equivalent airspeed.

    Parameters
    ----------
    equivalent_airspeed : float
        the equivalent airspeed in velocity_units
    mach : float
        the mach to hold constant
    alt_units : str; default='ft'
        the altitude units; ft, kft, m

    Returns
    -------
    alt : float
        the altitude in alt units
    """
    equivalent_airspeed = _convert_velocity(equivalent_airspeed, velocity_units, 'ft/s')
    dalt = 500.
    alt_old = 0.
    alt_final = 5000.
    n = 0
    tol = 5. # ft

    R = 1716.
    z0 = 0.
    T0 = atm_temperature(z0)
    p0 = atm_pressure(z0)
    k = np.sqrt(T0 / p0)
    #eas = a * mach * sqrt((p * T0) / (T * p0)) = a * mach * sqrt(p / T) * k

    # Newton's method
    while abs(alt_final - alt_old) > tol and n < 20:
        alt_old = alt_final
        alt1 = alt_old
        alt2 = alt_old + dalt
        T1 = atm_temperature(alt1)
        T2 = atm_temperature(alt2)
        press1 = atm_pressure(alt1)
        press2 = atm_pressure(alt2)
        sos1 = np.sqrt(1.4 * R * T1)
        sos2 = np.sqrt(1.4 * R * T2)
        eas1 = sos1 * mach * np.sqrt(press1 / T1) * k
        eas2 = sos2 * mach * np.sqrt(press2 / T2) * k
        m = dalt / (eas2 - eas1)
        alt_final = m * (equivalent_airspeed - eas1) + alt1
        n += 1

    if n > 18:
        print('n = %s' % n)
    alt_final = convert_altitude(alt_final, 'ft', alt_units)
    return alt_final

def get_alt_for_q_mach(q, mach, SI=False):
    """
    Gets the altitude associated with a equivalent airspeed.

    Parameters
    ----------
    q : float
        the dynamic pressure lb/ft^2 (SI=Pa)
    mach : float
        the mach to hold constant
    SI : bool
        should SI units be used; default=False

    Returns
    -------
    alt : float
        the altitude in ft (SI=m)
    """
    pressure = 2 * q / (1.4 * mach ** 2) # gamma = 1.4
    if SI:
        alt_units = 'm'
        pressure_units = 'Pa'
    else:
        alt_units = 'ft'
        pressure_units = 'psf'
    alt = get_alt_for_pressure(pressure, pressure_units=pressure_units, alt_units=alt_units)
    return alt

def get_alt_for_pressure(pressure, pressure_units='psf', alt_units='ft'):
    """
    Gets the altitude associated with a equivalent airspeed.

    Parameters
    ----------
    pressure : float
        the pressure lb/ft^2 (SI=Pa)
    pressure_units : str; default='psf'
        the pressure units; psf, psi, Pa
    alt_units : str; default='ft'
        the altitude units; ft, kft, m

    Returns
    -------
    alt : float
        the altitude in alt_units
    """
    pressure = _convert_pressure(pressure, pressure_units, 'psf')
    dalt = 500.
    alt_old = 0.
    alt_final = 5000.
    n = 0
    tol = 5. # ft

    # Newton's method
    while abs(alt_final - alt_old) > tol and n < 20:
        alt_old = alt_final
        alt1 = alt_old
        alt2 = alt_old + dalt
        press1 = atm_pressure(alt1)
        press2 = atm_pressure(alt2)
        m = dalt / (press2 - press1)
        alt_final = m * (pressure - press1) + alt1
        n += 1

    if n > 18:
        print('n = %s' % n)

    alt_final = convert_altitude(alt_final, 'ft', alt_units)
    return alt_final

def _feet_to_alt_units(alt_units):
    if alt_units == 'm':
        factor = 0.3048
    elif alt_units == 'ft':
        factor = 1.
    else:
        raise RuntimeError('alt_units=%r is not valid; use [ft, m]' % alt_units)
    return factor

def convert_altitude(alt, alt_units_in, alt_units_out):
    """nominal unit is ft"""
    if alt_units_in == alt_units_out:
        return alt

    factor = 1.0
    # units to feet
    if alt_units_in == 'm':
        factor /= 0.3048
    elif alt_units_in == 'ft':
        pass
    elif alt_units_in == 'kft':
        factor *= 1000.
    else:
        raise RuntimeError('alt_units_in=%r is not valid; use [ft, m, kft]' % alt_units_in)

    # ft to m
    if alt_units_out == 'm':
        factor *= 0.3048
    elif alt_units_out == 'ft':
        pass
    elif alt_units_out == 'kft':
        factor /= 1000.
    else:
        raise RuntimeError('alt_units_out=%r is not valid; use [ft, m, kft]' % alt_units_out)
    return alt * factor

def convert_velocity(velocity, velocity_units_in, velocity_units_out):
    """nominal unit is ft/s"""
    if velocity_units_in == velocity_units_out:
        return velocity

    factor = 1.0
    if velocity_units_in == 'm/s':
        factor /= 0.3048
    elif velocity_units_in == 'ft/s':
        pass
    elif velocity_units_in == 'in/s':
        factor /= 12.
    elif velocity_units_in == 'knots':
        factor *= 1.68781
    else:
        msg = 'velocity_units_in=%r is not valid; use [ft/s, m/s, knots]' % velocity_units_in
        raise RuntimeError(msg)

    if velocity_units_out == 'm/s':
        factor *= 0.3048
    elif velocity_units_out == 'ft/s':
        pass
    elif velocity_units_out == 'in/s':
        factor *= 12.
    elif velocity_units_out == 'knots':
        factor /= 1.68781
    else:
        msg = 'velocity_units_out=%r is not valid; use [ft/s, m/s, in/s, knots]' % velocity_units_out
        raise RuntimeError(msg)
    return velocity * factor

def convert_pressure(pressure, pressure_units_in, pressure_units_out):
    """nominal unit is psf"""
    if pressure_units_in == pressure_units_out:
        return pressure

    factor = 1.0
    if pressure_units_in == 'psf':
        pass
    elif pressure_units_in == 'psi':
        factor *= 144
    elif pressure_units_in == 'Pa':
        factor /= 47.880172
    else:
        msg = 'pressure_units_in=%r is not valid; use [psf, psi, Pa]' % pressure_units_in
        raise RuntimeError(msg)

    if pressure_units_out == 'psf':
        pass
    elif pressure_units_out == 'psi':
        factor /= 144
    elif pressure_units_out == 'Pa':
        factor *= 47.880172
    else:
        msg = 'pressure_units_out=%r is not valid; use [psf, psi, Pa]' % pressure_units_out
        raise RuntimeError(msg)
    return pressure * factor

def convert_density(density, density_units_in, density_units_out):
    """nominal unit is slug/ft^3"""
    if density_units_in == density_units_out:
        return density

    factor = 1.0
    if density_units_in == 'slug/ft^3':
        pass
    elif density_units_in == 'slinch/in^3':
        factor *= 12**4
    elif density_units_in == 'kg/m^3':
        factor /= 515.378818
    else:
        msg = 'density_units_in=%r is not valid; use [slug/ft^3]' % density_units_in
        raise RuntimeError(msg)

    # data is now in slug/ft^3
    if density_units_out == 'slug/ft^3':
        pass
    elif density_units_out == 'slinch/in^3':
        factor /= 12**4
    elif density_units_out == 'kg/m^3':
        factor *= 515.378818
    else:
        msg = 'density_units_out=%r is not valid; use [slug/ft^3, slinch/in^3]' % density_units_out
        raise RuntimeError(msg)
    return density * factor

def _rankine_to_kelvin(SI):
    if SI:
        factor = 5 / 9.
    else:
        factor = 1.
    return factor

def atm_temperature(alt, alt_units='ft', temperature_units='R'):
    r"""
    Freestream Temperature \f$ T_{\infty} \f$

    Parameters
    ----------
    alt : float
        Altitude in alt_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    temperature_units : str; default='R'
        the altitude units; R, K

    Returns
    -------
    T : float
        temperature in degrees Rankine or Kelvin (SI)

    .. note ::
        from BAC-7006-3352-001-V1.pdf  # Bell Handbook of Aerodynamic Heating\n
        page ~236 - Table C.1\n
        These equations were used because they are valid to 300k ft.\n
        Extrapolation is performed above that.
    """
    z = _update_alt(alt, alt_units)
    if z < 36151.725:
        T = 518.0 - 0.003559996 * z
    elif z < 82344.678:
        T = 389.988
    elif z < 155347.756:
        T = 389.988 + .0016273286 * (z - 82344.678)
    elif z < 175346.171:
        T = 508.788
    elif z < 249000.304:
        T = 508.788 - .0020968273 * (z - 175346.171)
    elif z < 299515.564:
        T = 354.348
    else:
        #print("alt=%i kft > 299.5 kft" % (z / 1000.))
        T = 354.348
        #raise AtmosphereError("altitude is too high")

    if temperature_units == 'R':
        factor = 1.
    elif temperature_units == 'K':
        factor = 5. / 9.
    else:
        raise RuntimeError('temperature_units=%r is not valid; use [ft, m]' % temperature_units)

    T2 = T * factor
    return T2

def atm_pressure(alt, alt_units='ft', pressure_units='psf', debug=False):
    r"""
    Freestream Pressure \f$ p_{\infty} \f$

    Parameters
    ----------
    alt : float
        Altitude in alt_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    pressure_units : str; default='psf'
        the pressure units; psf, psi, Pa

    Returns
    -------
    pressure : float
        Returns pressure in pressure_units

    .. note ::
        from BAC-7006-3352-001-V1.pdf  # Bell Handbook of Aerodynamic Heating\n
        page ~236 - Table C.1\n
        These equations were used b/c they are valid to 300k ft.\n
        Extrapolation is performed above that.\n
    """
    z = _update_alt(alt, alt_units)
    if z < 36151.725:
        lnP = 7.657389 + 5.2561258 * log(1 - 6.8634634E-6 * z)
    elif z < 82344.678:
        lnP = 6.158411 - 4.77916918E-5 * (z - 36151.725)
    elif z < 155347.756:
        lnP = 3.950775 - 11.3882724 * log(1.0 + 4.17276598E-6 * (z - 82344.678))
    elif z < 175346.171:
        lnP = 0.922461 - 3.62635373E-5*(z - 155347.756)
    elif z < 249000.304:
        lnP = 0.197235 + 8.7602095 * log(1.0 - 4.12122002E-6 * (z - 175346.171))
    elif z < 299515.564:
        lnP = -2.971785 - 5.1533546650E-5 * (z - 249000.304)
    else:
        #print("alt=%i kft > 299.5 kft" % (z / 1000.))
        lnP = -2.971785 - 5.1533546650E-5 * (z - 249000.304)

    p = exp(lnP)

    factor = convert_pressure(1., 'psf', pressure_units)
    return p * factor

def atm_dynamic_pressure(alt, mach, alt_units='ft', pressure_units='psf'):
    r"""
    Freestream Dynamic Pressure  \f$ q_{\infty} \f$

    Parameters
    ----------
    alt : float
        Altitude in alt_units
    mach : float
        Mach Number \f$ M \f$
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    pressure_units : str; default='psf'
        the pressure units; psf, psi, Pa

    Returns
    -------
    dynamic_pressure : float
        Returns dynamic pressure in pressure_units

    The common method that requires many calculations...
    \f[  \large q = \frac{1}{2} \rho V^2  \f]
    \f[  \large p = \rho R T  \f]
    \f[  \large M = \frac{V}{a}  \f]
    \f[  \large a = \sqrt{\gamma R T}  \f]
    so...
    \f[  \large q = \frac{\gamma}{2} p M^2  \f]
    """
    z = _update_alt(alt, alt_units)
    p = atm_pressure(z)
    q = 0.7 * p * mach ** 2

    factor = convert_pressure(1., 'psf', pressure_units)
    q2 = q * factor
    return q2

def atm_speed_of_sound(alt, alt_units='ft', velocity_units='ft/s', gamma=1.4):
    r"""
    Freestream Speed of Sound  \f$ a_{\infty} \f$

    Parameters
    ----------
    alt : bool
        Altitude in alt_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    velocity_units : str; default='ft/s'
        the velocity units; ft/s, m/s, in/s, knots

    Returns
    -------
    speed_of_sound, a : float
        Returns speed of sound in velocity_units

   \f[  \large a = \sqrt{\gamma R T}  \f]
    """
    # converts everything to English units first
    z = _update_alt(alt, alt_units)
    T = atm_temperature(z)
    R = 1716. # 1716.59, dir air, R=287.04 J/kg*K

    a = (gamma * R * T) ** 0.5
    factor = convert_velocity(1., 'ft/s', velocity_units) # ft/s to m/s
    a2 = a * factor
    return a2

def atm_velocity(alt, mach, alt_units='ft', velocity_units='ft/s'):
    r"""
    Freestream Velocity  \f$ V_{\infty} \f$

    Parameters
    ----------
    alt : float
        altitude in alt_units
    Mach : float
        Mach Number \f$ M \f$
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    velocity_units : str; default='ft/s'
        the velocity units; ft/s, m/s, in/s, knots

    Returns
    -------
    velocity : float
        Returns velocity in velocity_units

    \f[ \large V = M a \f]
    """
    a = atm_speed_of_sound(alt, alt_units=alt_units, velocity_units=velocity_units)
    V = mach * a # units=ft/s or m/s
    return V

def atm_equivalent_airspeed(alt, mach, alt_units='ft', eas_units='ft/s'):
    """
    Parameters
    ----------
    alt : float
        altitude in alt_units
    Mach : float
        Mach Number \f$ M \f$
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    velocity_units : str; default='ft/s'
        the velocity units; ft/s, m/s, in/s, knots

    Returns
    -------
    eas : float
        equivalent airspeed in velocity_units

    EAS = TAS * sqrt(rho/rho0)
    p = rho * R * T
    rho = p/(RT)
    rho/rho0 = p/T * T0/p0
    TAS = a * M
    EAS = a * M * sqrt(p/T * T0/p0)
    EAS = a * M * sqrt(p*T0 / (T*p0))
    """
    z = convert_altitude(alt, alt_units, 'ft')
    a = atm_speed_of_sound(z)
    #V = mach * a # units=ft/s or m/s

    z0 = 0.
    T0 = atm_temperature(z0)
    p0 = atm_pressure(z0)

    T = atm_temperature(z)
    p = atm_pressure(z)

    eas = a * mach * np.sqrt((p * T0) / (T * p0))
    eas2 = convert_velocity(eas, 'ft/s', eas_units)
    return eas2

def atm_mach(alt, V, alt_units='ft', velocity_units='ft/s'):
    r"""
    Freestream Mach Number

    Parameters
    ----------
    alt : float
        altitude in alt_units
    V : float
        Velocity in velocity_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    velocity_units : str; default='ft/s'
        the velocity units; ft/s, m/s, in/s, knots

    Returns
    -------
    mach : float
        Mach Number \f$ M \f$

    \f[ \large M = \frac{V}{a} \f]
    """
    a = atm_speed_of_sound(alt, alt_units=alt_units, velocity_units=velocity_units)
    mach = V / a
    return mach

def atm_density(alt, R=1716., alt_units='ft', density_units='slug/ft^3'):
    r"""
    Freestream Density   \f$ \rho_{\infty} \f$

    Parameters
    ----------
    alt : float
        altitude in feet or meters
    R : float; default=1716.
        gas constant for air in english units (???)
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    density_units : str; default='slug/ft^3'
        the density units; slug/ft^3, slinch/in^3, kg/m^3

    Returns
    -------
    rho : float
        density \f$ \rho \f$ in density_units

    Based on the formula P=pRT
    \f[ \large \rho=\frac{p}{R T} \f]
    """
    z = _update_alt(alt, alt_units)
    P = atm_pressure(z)
    T = atm_temperature(z)

    rho = P / (R * T)
    rho2 = convert_density(rho, 'slug/ft^3', density_units)
    return rho2

def atm_kinematic_viscosity_nu(alt, alt_units='ft', visc_units='ft^2/s', debug=False):
    r"""
    Freestream Kinematic Viscosity \f$ \nu_{\infty} \f$

    Parameters
    ----------
    alt : bool
        Altitude in alt_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    visc_units : str; default='slug/ft^3'
        the kinematic viscosity units; ft^2/s, m^2/s

    Returns
    -------
    nu : float
        kinematic viscosity \f$ \nu_{\infty} \f$ in visc_units

    \f[ \large \nu = \frac{\mu}{\rho} \f]

    .. see ::  SutherlandVisc
    .. todo:: better debug
    """
    z = _update_alt(alt, alt_units)
    rho = atm_density(z)
    mu = atm_dynamic_viscosity_mu(z)
    nu = mu / rho
    if debug:  # doesnt work unless US units
        print("atm_nu - rho=%g [slug/ft^3] mu=%e [lb*s/ft^2] nu=%e [ft^2/s]" % (rho, mu, nu))

    if visc_units == 'ft^2/s':
        factor = 1.
    elif visc_units == 'm^2/s':
        factor = _feet_to_alt_units(alt_units) ** 2
    else:
        raise NotImplementedError('visc_units=%r' % visc_units)
    return nu * factor

def atm_dynamic_viscosity_mu(alt, alt_units='ft', visc_units='(lbf*s)/ft^2'):
    r"""
    Freestream Dynamic Viscosity  \f$ \mu_{\infty} \f$

    Parameters
    ----------
    alt : bool
        Altitude in alt_units
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    visc_units : str; default='(lbf*s)/ft^2'
        the viscosity units; (lbf*s)/ft^2, (N*s)/m^2, Pa*s

    Returns
    -------
    mu : float
        dynamic viscosity  \f$ \mu_{\infty} \f$ in (lbf*s)/ft^2 or (N*s)/m^2 (SI)

    .. see ::  SutherlandVisc
    """
    z = _update_alt(alt, alt_units)
    T = atm_temperature(z)
    mu = sutherland_viscoscity(T)  # (lbf*s)/ft^2
    if visc_units == '(lbf*s)/ft^2':
        factor = 1.
    elif visc_units in ['(N*s)/m^2', 'Pa*s']:
        factor = 47.88026
    else:
        raise NotImplementedError('visc_units=%r; not in (lbf*s)/ft^2 or (N*s)/m^2 or Pa*s')
    return mu * factor

def atm_unit_reynolds_number2(alt, mach, alt_units='ft', ReL_units='1/ft', debug=False):
    r"""
    Returns the Reynolds Number per unit length

    Parameters
    ----------
    alt : bool
        Altitude in alt_units
    mach : float
        Mach Number \f$ M \f$
    alt_units : str; default='ft'
        the altitude units; ft, kft, m
    ReL_units : str; default='1/ft'
        the altitude units; 1/ft, 1/m

    Returns
    -------
    ReynoldsNumber/L : float
        the Reynolds Number per unit length

    \f[ \large Re_L = \frac{ \rho V}{\mu} = \frac{p M a}{\mu R T} \f]

    .. note ::
        this version of Reynolds number directly caculates the base quantities, so multiple
        calls to atm_press and atm_temp are not made
    """
    z = _update_alt(alt, alt_units)
    #print("z = ",z)
    gamma = 1.4
    R = 1716.
    p = atm_pressure(z)
    T = atm_temperature(z)
    #p = rhoRT
    a = (gamma * R * T) ** 0.5
    mu = sutherland_viscoscity(T)
    ReL = p * a * mach / (mu * R * T)

    if debug:
        print("---atm_UnitReynoldsNumber2---")
        print("z  = %s [m]   = %s [ft]"  % (alt * _feet_to_alt_units('m'), z))
        print("a  = %s [m/s] = %s [ft/s]"  % (a * _feet_to_alt_units('m'), a))
        rho = p / (R * T)
        print("rho = %s [kg/m^3] = %s [slug/ft^3]"  % (rho * 515.378818, rho))
        print("M  = %s"  % mach)
        print("V  = %s [m/s] = %s [ft/s]"  % (a * mach * _feet_to_alt_units('m'), a * mach))
        print("T  = %s [K] = %s [R]" % (T * 5 / 9., T))
        print("mu = %s [(N*s)/m^2] = %s [(lbf*s)/ft^2]" % (mu * 47.88026, mu))
        print("Re = %s [1/m] = %s [1/ft]" % (ReL / 0.3048, ReL))

    # convert ReL in 1/ft to 1/m
    if ReL_units == '1/ft':
        factor = 1.
    elif ReL_units == '1/m':
        factor = 1. / .3048
    else:
        raise NotImplementedError(ReL_units)
    return ReL * factor

def atm_unit_reynolds_number(alt, mach, SI=False, debug=False):
    r"""
    Returns the Reynolds Number per unit length

    Parameters
    ----------
    alt : bool
        Altitude in feet or meters (SI)
    mach : float
        Mach Number \f$ M \f$
    SI : bool; default=False
        convert to SI units

    Returns
    -------
    ReynoldsNumber/L : float
        1/ft or 1/m (SI)

    \f[ \large Re   = \frac{ \rho V L}{\mu} \f]
    \f[ \large Re_L = \frac{ \rho V  }{\mu} \f]
    """
    z = _update_alt(alt, SI)
    rho = atm_density(z)
    V = atm_velocity(z, mach)
    mu = atm_dynamic_viscosity_mu(z)

    ReL = (rho * V) / mu

    if debug:
        print("---atm_UnitReynoldsNumber---")
        print("z  = %s [m]   = %s [ft]"  % (alt * _feet_to_alt_units('m'), z))
        print("rho = %s [kg/m^3] = %s [slug/ft^3]"  % (rho * 515.378818, rho))
        print("V  = %s [m/s] = %s [ft/s]"  % (V * _feet_to_alt_units('m'), V))
        print("mu = %s [(N*s)/m^2] = %s [(lbf*s)/ft^2]" % (mu * 47.88026, mu))
        print("Re = %s [1/m] = %s [1/ft]" % (ReL / 0.3048, ReL))

    if SI:
        return ReL / .3048  # convert ReL in 1/ft to 1/m
    return ReL

def sutherland_viscoscity(T):
    r"""
    Helper function that calculates the dynamic viscosity \f$ \mu \f$ of air at
    a given temperature

    Parameters
    ----------
    T : float
        Temperature T is in Rankine

    Returns
    -------
    mu : float
       dynamic viscosity  \f$ \mu \f$ of air in (lbf*s)/ft^2

    .. note ::
        prints a warning if T>5400 deg R

    Sutherland's Equation\n
    From Aerodynamics for Engineers 4th Edition\n
    John J. Bertin 2002\n
    page 6 eq 1.5b\n
    """
    if T < 225.: # Rankine
        viscosity = 8.0382436E-10 * T
    else:
        if T > 5400.:
            msg = "WARNING:  viscosity - Temperature is too large (T>5400) T=%s\n" % T
            sys.stderr.write(msg)
        viscosity = 2.27E-8 * (T ** 1.5) / (T + 198.6)
    return viscosity
