import json, os, glob
import numpy as np


def extract_lost_frames_from_json(cam_json):
    
    lost_count = cam_json['RecordingReport']['FramesLostCount']
    if lost_count == 0:
        return []
    
    lost_string = cam_json['RecordingReport']['LostFrames'][0]
    lost_spans = lost_string.split(',')
    
    lost_frames = []
    for span in lost_spans:
        
        start_end = span.split('-')
        if len(start_end)==1:
            lost_frames.append(int(start_end[0]))
        else:
            lost_frames.extend(np.arange(int(start_end[0]), int(start_end[1])+1))
    
    return np.array(lost_frames)-1 #you have to subtract one since the json starts indexing at 1 according to Totte
    

def get_frame_exposure_times(sync_dataset, cam_json):
    
    if isinstance(cam_json, str):
        cam_json = read_json(cam_json)
        
    exposure_sync_line_label_dict = {
            'Eye': 'eye_cam_exposing',
            'Face': 'face_cam_exposing',
            'Behavior': 'beh_cam_exposing'}
    
    cam_label =  cam_json['RecordingReport']['CameraLabel']
    sync_line = exposure_sync_line_label_dict[cam_label]
    
    exposure_times = sync_dataset.get_rising_edges(sync_line, units='seconds')
    
    lost_frames = extract_lost_frames_from_json(cam_json)

    total_frames = cam_json['FramesRecorded']
    
    frame_times = [e for ie, e in enumerate(exposure_times) if ie not in lost_frames]
    frame_times = frame_times[:total_frames] #trim extra exposures
    frame_times = np.insert(frame_times, 0, 0) #insert dummy time for metadata frame
    
    return np.array(frame_times)


def read_json(jsonfilepath):
    
    with open(jsonfilepath, 'r') as f:
        contents = json.load(f)
    
    return contents