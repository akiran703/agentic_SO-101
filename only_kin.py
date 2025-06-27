import math
from typing import Tuple,Dict,Any


class KinematicsM:
    
    def __init__(self,param) -> None:
            self.L1 = param['L1']
            self.L2 = param['L2']
            self.SL : Dict[str, Tuple[float, float]] = param['SPATIAL_LIMITS']
            self.BHMM = param['BASE_HEIGHT_MM']
            self.SMOMM = param['SHOULDER_MOUNT_OFFSET_MM']
            self.EMOMM = param['ELBOW_MOUNT_OFFSET_MM']
            
            #offset in RAD
            self.SMOMMRAD = math.asin(self.SMOMM/ self.L1)
            self.EMOMMRAD = math.asin(self.EMOMM/ self.L2)
    
    #calculate the x,z position of the wrist flex motor based on shoulder lift and elbow flex 
    def forward_kin(self,shoulder_lift_deg,elbow_flex_deg) -> tuple[float,float]:
        
            ang_shoulder_fk = math.radians(shoulder_lift_deg) + self.SMOMMRAD
            ang_elbow_fk = math.radians(elbow_flex_deg) + self.EMOMMRAD
            x = -self.L1 * math.cos(ang_shoulder_fk)  + self.L2 * math.cos(ang_elbow_fk)
            z = self.L1 * math.sin(ang_shoulder_fk) + self.L2 * math.sin(ang_elbow_fk) + self.BHMM
            
            return x,z
        
    #calculate shoulder lift and elbow angle for target X,Z 
    def inverse_kin(self,target_x,target_z) -> tuple[float,float]:
        #find the hypoth of blue triangle
        z_adj = target_z - self.BHMM
        hypoth_d = target_x**2 + z_adj**2
        d = math.sqrt(hypoth_d)
        
        #first component to find angle one
        phi1 = math.atan2(z_adj, target_x)
        #second component to find angle one
        phi2 = math.acos(min(1.0, max(-1.0, (self.L1**2 + hypoth_d - self.L2**2) / (2 * self.L1 * d)))) 
        
        #angle1 in rad
        shoulder_lift_deg = 180.0 - math.degrees(phi1 + phi2) - math.degrees(self.SMOMMRAD)
        angle1 = math.radians(shoulder_lift_deg) + self.SMOMMRAD
        
        #set up to find angle 2 (works when angle2 is greater than 180 degrees)
        cos2_arg = min(1.0, max(-1.0, (target_x + self.L1 * math.cos(angle1)) / self.L2))
        sin2_arg = min(1.0, max(-1.0, (z_adj - self.L1 * math.sin(angle1)) / self.L2))
        angle2 = math.atan2(sin2_arg, cos2_arg)     
        
        #cal wrist flex since the change in angle 1 and angle 2 will effect wrist tilt
        elbow_flex_deg = math.degrees(angle2 + math.radians(shoulder_lift_deg)) - math.degrees(self.EMOMMRAD)
        
        
        return shoulder_lift_deg, elbow_flex_deg
        

    #validate if the x and z are within spatial and reach limits 
    def is_valid_target_cart(self,x,z) -> tuple[bool,str]:
        if not (self.SL["x"][0] <= x <= self.SL["x"][1]):
            return False, f"Target X {x:.1f}mm out of range {self.SL['x']}"
        
        if not (self.SL["z"][0] <= z <= self.SL["z"][1]):
            return False, f"Target Z {z:.1f}mm out of range {self.SL['z']}"
        if x < 20 and z < 150:
            return False, f"Target ({x:.1f},{z:.1f})mm violates: if x < 20mm, z must be >= 150mm."
        
        z_adj = z - self.BHMM
        distance = math.sqrt(z_adj**2 + x**2)
        max_reach = self.L1 + self.L2
        
        if distance > max_reach - 1:
            return False, f"Target ({x:.1f},{z:.1f})mm is beyond max reach {max_reach-1:.1f}mm (safety margin: 1mm), distance is {distance:.1f}mm"
        return True, "Valid" 