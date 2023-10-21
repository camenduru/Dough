import streamlit as st
from ui_components.widgets.frame_movement_widgets import change_position_input, delete_frame_button, jump_to_single_frame_view_button, move_frame_back_button, move_frame_forward_button, replace_image_widget
from ui_components.widgets.frame_time_selector import single_frame_time_selector, single_frame_time_duration_setter
from ui_components.widgets.image_carousal import display_image
from utils.data_repo.data_repo import DataRepo
from ui_components.constants import WorkflowStageType
from utils import st_memory
from ui_components.methods.file_methods import generate_pil_image
from ui_components.widgets.add_key_frame_element import add_key_frame


def timeline_view_buttons(i, j, timing_details, shift_frames_setting, time_setter_toggle, replace_image_widget_toggle, duration_setter_toggle, copy_frame_toggle, move_frames_toggle, delete_frames_toggle, change_position_toggle, project_uuid):
    data_repo = DataRepo()
    if time_setter_toggle:
        single_frame_time_selector(timing_details[i + j].uuid, 'motion', shift_frames=shift_frames_setting)                                    
    if duration_setter_toggle:
        single_frame_time_duration_setter(timing_details[i + j].uuid, 'motion', shift_frames=shift_frames_setting)
    if replace_image_widget_toggle:
        replace_image_widget(timing_details[i + j].uuid, stage=WorkflowStageType.STYLED.value,options=["Uploaded Frame"])
    
    btn1, btn2, btn3, btn4 = st.columns([1, 1, 1, 1])
    
    if move_frames_toggle:
        with btn1:                                            
            move_frame_back_button(timing_details[i + j].uuid, "side-to-side")
        with btn2:   
            move_frame_forward_button(timing_details[i + j].uuid, "side-to-side")
    
    if copy_frame_toggle:
        with btn3:
            if st.button("🔁", key=f"copy_frame_{timing_details[i + j].uuid}"):
                pil_image = generate_pil_image(timing_details[i + j].primary_image.location)
                position_of_current_item = timing_details[i + j].aux_frame_index
                add_key_frame(pil_image, False, 2.5, timing_details[i + j].aux_frame_index+1, refresh_state=False)

                st.rerun()

    if delete_frames_toggle:
        with btn4:
            delete_frame_button(timing_details[i + j].uuid)
    
    if change_position_toggle:
        change_position_input(timing_details[i + j].uuid, "side-to-side")        

    if time_setter_toggle or duration_setter_toggle or replace_image_widget_toggle or move_frames_toggle or delete_frames_toggle or change_position_toggle:
        st.caption("--")
    
    jump_to_single_frame_view_button(i + j + 1, timing_details, 'timeline_btn_'+str(timing_details[i+j].uuid))        


def timeline_view(project_uuid, stage):
    data_repo = DataRepo()
    timing_details = data_repo.get_timing_list_from_project(project_uuid)

    header_col_1, header_col_2, header_col_3 = st.columns([1.5,4,1.5])
    
    with header_col_1:
        shift_frames_setting = st.toggle("Shift Frames", help="If set to True, it will shift the frames after your adjustment forward by the amount of time you move.")

    with header_col_2:
        col1, col2, col3 = st.columns(3)

        with col1:
            expand_all = st_memory.toggle("Expand All", key="expand_all",value=False)
        
        if expand_all:
            time_setter_toggle = replace_image_widget_toggle = duration_setter_toggle = copy_frame_toggle = move_frames_toggle = delete_frames_toggle = change_position_toggle = True
            
        else:           
            with col2:     
                time_setter_toggle = st_memory.toggle("Time Setter", value=True, key="time_setter_toggle")
                delete_frames_toggle = st_memory.toggle("Delete Frames", value=True, key="delete_frames_toggle")                
                duration_setter_toggle = st_memory.toggle("Duration Setter", value=False, key="duration_setter_toggle")
                copy_frame_toggle = st_memory.toggle("Copy Frame", value=False, key="copy_frame_toggle")
            with col3:
                move_frames_toggle = st_memory.toggle("Move Frames", value=True, key="move_frames_toggle")
                replace_image_widget_toggle = st_memory.toggle("Replace Image", value=False, key="replace_image_widget_toggle")
                change_position_toggle = st_memory.toggle("Change Position", value=False, key="change_position_toggle")

    with header_col_3:
        items_per_row = st_memory.slider("How many frames per row?", min_value=1, max_value=10, value=5, step=1, key="items_per_row_slider")
    
    st.markdown("***")
    total_count = len(timing_details)
    for i in range(0, total_count, items_per_row):  # Step of items_per_row for grid
        grid = st.columns(items_per_row)  # Create items_per_row columns for grid
        for j in range(items_per_row):
            if i + j < total_count:  # Check if index is within range
                with grid[j]:
                    display_number = i + j + 1                            
                    if stage == 'Key Frames':
                        display_image(timing_uuid=timing_details[i + j].uuid, stage=WorkflowStageType.STYLED.value, clickable=False)
                    elif stage == 'Videos':
                        if timing_details[i + j].timed_clip:
                            st.video(timing_details[i + j].timed_clip.location)
                        else:
                            st.error("No video found for this frame.")
                    with st.expander(f'Frame #{display_number}', True):    
                        timeline_view_buttons(i, j, timing_details, shift_frames_setting, time_setter_toggle, replace_image_widget_toggle, duration_setter_toggle, copy_frame_toggle, move_frames_toggle, delete_frames_toggle, change_position_toggle, project_uuid)


