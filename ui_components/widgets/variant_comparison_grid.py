import json
import time
import ast
import streamlit as st
import re
from shared.constants import InferenceParamType, InternalFileTag
from ui_components.constants import CreativeProcessType
from ui_components.methods.common_methods import promote_image_variant, promote_video_variant
from ui_components.methods.file_methods import create_duplicate_file
from ui_components.methods.video_methods import sync_audio_and_duration
from ui_components.widgets.shot_view import create_video_download_button
from ui_components.models import InternalFileObject
from ui_components.widgets.add_key_frame_element import add_key_frame
from ui_components.widgets.animation_style_element import update_interpolation_settings
from utils.data_repo.data_repo import DataRepo



def variant_comparison_grid(ele_uuid, stage=CreativeProcessType.MOTION.value):
    '''
    UI element which compares different variant of images/videos. For images ele_uuid has to be timing_uuid
    and for videos it has to be shot_uuid.
    '''
    data_repo = DataRepo()

    timing_uuid, shot_uuid = None, None
    if stage == CreativeProcessType.MOTION.value:
        shot_uuid = ele_uuid
        shot = data_repo.get_shot_from_uuid(shot_uuid)
        variants = shot.interpolated_clip_list
        timing_list = data_repo.get_timing_list_from_shot(shot.uuid)
    else:
        timing_uuid = ele_uuid        
        timing = data_repo.get_timing_from_uuid(timing_uuid)
        variants = timing.alternative_images_list
        shot_uuid = timing.shot.uuid
        timing_list =""

    

    col1, col2, col3 = st.columns([1, 1,0.5])
    if stage == CreativeProcessType.MOTION.value:
        items_to_show = 2
        num_columns = 3
        with col1:
            st.markdown(f"### 🎞️ '{shot.name}' options  _________")
            st.write("##### _\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_")
    else:
        items_to_show = 5
            
        num_columns = 3

    # Updated logic for pagination
    num_pages = (len(variants) - 1) // items_to_show + ((len(variants) - 1) % items_to_show > 0)
    page = 1

    if num_pages > 1:
        page = col3.radio('Page:', options=list(range(1, num_pages + 1)), horizontal=True)

    if not len(variants):
        st.info("No options created yet.")
        st.markdown("***")
    else:
        current_variant = shot.primary_interpolated_video_index if stage == CreativeProcessType.MOTION.value else int(timing.primary_variant_index)

        st.markdown("***")
        cols = st.columns(num_columns)
        with cols[0]:
            h1, h2 = st.columns([1, 1])
            with h1:
                st.info(f"###### Variant #{current_variant + 1}")
            with h2:
                st.success("**Main variant**")
            # Display the main variant
            if stage == CreativeProcessType.MOTION.value:
                st.video(variants[current_variant].location, format='mp4', start_time=0) if (current_variant != -1 and variants[current_variant]) else st.error("No video present")
                create_video_download_button(variants[current_variant].location, tag="var_compare")
                variant_inference_detail_element(variants[current_variant], stage, shot_uuid, timing_list, tag="var_compare")                        

            else:
                st.image(variants[current_variant].location, use_column_width=True)

            

        # Determine the start and end indices for additional variants on the current page
        additional_variants = [idx for idx in range(len(variants) - 1, -1, -1) if idx != current_variant]
        page_start = (page - 1) * items_to_show
        page_end = page_start + items_to_show
        page_indices = additional_variants[page_start:page_end]

        next_col = 1
        for i, variant_index in enumerate(page_indices):

            with cols[next_col]:
                h1, h2 = st.columns([1, 1])
                with h1:
                    st.info(f"###### Variant #{variant_index + 1}")
                with h2:
                    if st.button(f"Promote Variant #{variant_index + 1}", key=f"Promote Variant #{variant_index + 1} for {st.session_state['current_frame_index']}", help="Promote this variant to the primary image", use_container_width=True):
                        if stage == CreativeProcessType.MOTION.value:
                            promote_video_variant(shot.uuid, variants[variant_index].uuid)
                        else:
                            promote_image_variant(timing.uuid, variant_index)                    
                        st.rerun()

                if stage == CreativeProcessType.MOTION.value:                    
                    st.video(variants[variant_index].location, format='mp4', start_time=0) if variants[variant_index] else st.error("No video present")
                    create_video_download_button(variants[variant_index].location, tag="var_details")
                    variant_inference_detail_element(variants[variant_index], stage, shot_uuid, timing_list, tag="var_details")

                else:
                    st.image(variants[variant_index].location, use_column_width=True) if variants[variant_index] else st.error("No image present")                
                
            
            next_col += 1
            if next_col >= num_columns or i == len(page_indices) - 1 or len(page_indices) == i:
                next_col = 0  # Reset the column counter
                st.markdown("***")  # Add markdown line
                cols = st.columns(num_columns)  # Prepare for the next row            
                # Add markdown line if this is not the last variant in page_indices

                
def variant_inference_detail_element(variant, stage, shot_uuid, timing_list="", tag="temp"):
    data_repo = DataRepo()
    shot = data_repo.get_shot_from_uuid(shot_uuid)
    inf_data = fetch_inference_data(variant)
    # st.write(inf_data)
    if stage == CreativeProcessType.MOTION.value:
        if st.button("Load up settings from this variant", key=f"{tag}_{variant.name}", help="This will remove the current settings and images - though they'll be available for all previous runs.", use_container_width=True):
                        
            dynamic_strength_values = inf_data["dynamic_strength_values"]
            dynamic_key_frame_influence_values = inf_data["dynamic_key_frame_influence_values"]
            dynamic_frame_distribution_values = inf_data["dynamic_frame_distribution_values"]            
            dynamic_frame_distribution_values = [int(float(i)) for i in dynamic_frame_distribution_values]
            context_length = inf_data["context_length"]
            context_stride = inf_data["context_stride"]
            context_overlap = inf_data["context_overlap"]
            multipled_base_end_percent = inf_data["multipled_base_end_percent"]
            individual_prompts = inf_data["individual_prompts"]
            individual_prompts = individual_prompts.replace('"""', '""')
            individual_negative_prompts = inf_data["individual_negative_prompts"]
            individual_negative_prompts = individual_negative_prompts.replace('"""', '""')                         
            motion_scales = inf_data["motion_scales"]
            buffer = inf_data["buffer"]     

            strength_of_frames, freedoms_between_frames, speeds_of_transitions, distances_to_next_frames, type_of_motion_context, strength_of_adherence, prompt_travel, negative_prompt_travel, motions_during_frames = reverse_data_transformation(
                dynamic_strength_values,
                dynamic_key_frame_influence_values,
                dynamic_frame_distribution_values,            
                context_length,
                context_stride,
                context_overlap,
                multipled_base_end_percent,
                individual_prompts,
                individual_negative_prompts,
                motion_scales,
                buffer
            )            

            if type_of_motion_context == "Low":
                st.session_state[f'type_of_motion_context_index_{shot.uuid}'] = 0
            elif type_of_motion_context == "Standard":
                st.session_state[f'type_of_motion_context_index_{shot.uuid}'] = 1
            else:
                st.session_state[f'type_of_motion_context_index_{shot.uuid}'] = 2
            
            st.session_state[f'strength_of_adherence_value_{shot.uuid}'] = strength_of_adherence
            
            for i in range(0, len(strength_of_frames)):

                st.session_state[f'strength_of_frame_{shot.uuid}_{i}'] = strength_of_frames[i]
                if i < len(prompt_travel):
                    st.session_state[f'individual_prompt_{shot.uuid}_{i}'] = prompt_travel[i] if prompt_travel[i] else ""
                else:
                    st.session_state[f'individual_prompt_{shot.uuid}_{i}'] = ""
                if i < len(negative_prompt_travel):
                    st.session_state[f'individual_negative_prompt_{shot.uuid}_{i}'] = negative_prompt_travel[i]
                else:
                    st.session_state[f'individual_negative_prompt_{shot.uuid}_{i}'] = ""
                st.session_state[f'motion_during_frame_{shot.uuid}_{i}'] = motions_during_frames[i]                                     
                
                if i < len(strength_of_frames) - 1:
                    st.session_state[f'freedom_between_frames_{shot.uuid}_{i}'] = freedoms_between_frames[i]                    
                    st.session_state[f'distance_to_next_frame_{shot.uuid}_{i}'] = distances_to_next_frames[i]
                    st.session_state[f'speed_of_transition_{shot.uuid}_{i}'] = speeds_of_transitions[i]                                                
        '''
        if st.button("Sync audio/duration", key=f"{tag}_{variant.uuid}", help="Updates video length and the attached audio", use_container_width=True):
            data_repo = DataRepo()
            _ = sync_audio_and_duration(variant, shot_uuid)
            _ = data_repo.get_shot_list(shot.project.uuid, invalidate_cache=True)
            st.success("Video synced")
            time.sleep(0.3)
            st.rerun()
        '''    
    
    inf_data = fetch_inference_data(variant)
    if 'image_prompt_list' in inf_data:
        del inf_data['image_prompt_list']
    if 'image_list' in inf_data:
        del inf_data['image_list']
    if 'output_format' in inf_data:
        del inf_data['output_format']
    
    # st.write(inf_data)
    
    if stage != CreativeProcessType.MOTION.value:
        h1, h2 = st.columns([1, 1])
        with h1:
            st.markdown(f"Add to shortlist:")
            add_variant_to_shortlist_element(variant, shot.project.uuid)
        with h2:
            add_variant_to_shot_element(variant, shot.project.uuid)




def prepare_values(inf_data, timing_list):
    settings = inf_data     # Map interpolation_type to indices
    interpolation_style_map = {
        'ease-in-out': 0,
        'ease-in': 1,
        'ease-out': 2,
        'linear': 3
    }

    values = {
        'type_of_frame_distribution': 1 if settings.get('type_of_frame_distribution') == 'dynamic' else 0,
        'linear_frame_distribution_value': settings.get('linear_frame_distribution_value', None),
        'type_of_key_frame_influence': 1 if settings.get('type_of_key_frame_influence') == 'dynamic' else 0,
        'length_of_key_frame_influence': float(settings.get('linear_key_frame_influence_value')) if settings.get('linear_key_frame_influence_value') else None,
        'type_of_cn_strength_distribution': 1 if settings.get('type_of_cn_strength_distribution') == 'dynamic' else 0,
        'linear_cn_strength_value': tuple(map(float, ast.literal_eval(settings.get('linear_cn_strength_value')))) if settings.get('linear_cn_strength_value') else None,
        'interpolation_style': interpolation_style_map[settings.get('interpolation_type')] if settings.get('interpolation_type', 'ease-in-out') in interpolation_style_map else None,
        'motion_scale': settings.get('motion_scale', None),            
        'negative_prompt_video': settings.get('negative_prompt', None),
        'relative_ipadapter_strength': settings.get('relative_ipadapter_strength', None),
        'relative_ipadapter_influence': settings.get('relative_ipadapter_influence', None),        
        'soft_scaled_cn_weights_multiple_video': settings.get('soft_scaled_cn_weights_multiplier', None)
    }

    # Add dynamic values
    dynamic_frame_distribution_values = settings['dynamic_frame_distribution_values'].split(',') if settings['dynamic_frame_distribution_values'] else []
    dynamic_key_frame_influence_values = settings['dynamic_key_frame_influence_values'].split(',') if settings['dynamic_key_frame_influence_values'] else []
    dynamic_cn_strength_values = settings['dynamic_cn_strength_values'].split(',') if settings['dynamic_cn_strength_values'] else []

    min_length = len(timing_list) if timing_list else 0

    for idx in range(min_length):

        # Process dynamic_frame_distribution_values
        if dynamic_frame_distribution_values:            
            values[f'dynamic_frame_distribution_values_{idx}'] = (
                int(dynamic_frame_distribution_values[idx]) 
                if dynamic_frame_distribution_values[idx] and dynamic_frame_distribution_values[idx].strip() 
                else None
            )        
        # Process dynamic_key_frame_influence_values
        if dynamic_key_frame_influence_values:            
            values[f'dynamic_key_frame_influence_values_{idx}'] = (
                float(dynamic_key_frame_influence_values[idx]) 
                if dynamic_key_frame_influence_values[idx] and dynamic_key_frame_influence_values[idx].strip() 
                else None
            )
        
        # Process dynamic_cn_strength_values
        if dynamic_cn_strength_values and idx * 2 <= len(dynamic_cn_strength_values):
            # Since idx starts from 1, we need to adjust the index for zero-based indexing
            adjusted_idx = idx * 2
            # Extract the two elements that form a tuple
            first_value = dynamic_cn_strength_values[adjusted_idx].strip('(')
            second_value = dynamic_cn_strength_values[adjusted_idx + 1].strip(')')
            # Convert both strings to floats and create a tuple
            value_tuple = (float(first_value), float(second_value))
            # Store the tuple in the dictionary with a key indicating its order
            values[f'dynamic_cn_strength_values_{idx}'] = value_tuple

    return values

def fetch_inference_data(file: InternalFileObject):
    if not file:
        return
    
    not_found_msg = 'No data available.'    
    inf_data = None
    # NOTE: generated videos also have other params stored inside origin_data > settings
    if file.inference_log and file.inference_log.input_params:
        inf_data = json.loads(file.inference_log.input_params)
        if 'origin_data' in inf_data and inf_data['origin_data']['inference_type'] == 'frame_interpolation':
            inf_data = inf_data['origin_data']['settings']
        else:
            for data_type in InferenceParamType.value_list():
                if data_type in inf_data:
                    del inf_data[data_type]
    
    inf_data = inf_data or not_found_msg

    return inf_data

def add_variant_to_shortlist_element(file: InternalFileObject, project_uuid):
    data_repo = DataRepo()
    
    if st.button("Add to shortlist ➕", key=f"shortlist_{file.uuid}",use_container_width=True, help="Add to shortlist"):
        duplicate_file = create_duplicate_file(file, project_uuid)
        data_repo.update_file(duplicate_file.uuid, tag=InternalFileTag.SHORTLISTED_GALLERY_IMAGE.value)
        st.success("Added To Shortlist")
        time.sleep(0.3)
        st.rerun()

def add_variant_to_shot_element(file: InternalFileObject, project_uuid):
    data_repo = DataRepo()

    shot_list = data_repo.get_shot_list(project_uuid)
    shot_names = [s.name for s in shot_list]
    
    shot_name = st.selectbox('Add to shot:', shot_names, key=f"current_shot_variant_{file.uuid}")
    if shot_name:
        if st.button(f"Add to shot", key=f"add_{file.uuid}", help="Promote this variant to the primary image", use_container_width=True):
            shot_number = shot_names.index(shot_name)
            shot_uuid = shot_list[shot_number].uuid

            duplicate_file = create_duplicate_file(file, project_uuid)
            add_key_frame(duplicate_file, False, shot_uuid, len(data_repo.get_timing_list_from_shot(shot_uuid)), refresh_state=False, update_cur_frame_idx=False)
            st.rerun()



def reverse_data_transformation(dynamic_strength_values, dynamic_key_frame_influence_values, dynamic_frame_distribution_values, context_length, context_stride, context_overlap, multipled_base_end_percent, formatted_individual_prompts, formatted_individual_negative_prompts, formatted_motions, buffer):

    def reverse_transform(dynamic_strength_values, dynamic_key_frame_influence_values, dynamic_frame_distribution_values):

        # Reconstructing strength_of_frames
        strength_of_frames = [strength for _, strength, _ in dynamic_strength_values]
        
        # Reconstructing freedoms_between_frames (correctly as movements_between_frames)
        freedoms_between_frames = []
        for i in range(1, len(dynamic_strength_values)):
            if dynamic_strength_values[i][0] is not None:
                middle_value = dynamic_strength_values[i][1]
                adjusted_value = dynamic_strength_values[i][0]
                relative_value = (middle_value - adjusted_value) / middle_value
                freedoms_between_frames.append(round(relative_value, 2))  # Ensure proper rounding
        
        # Reconstructing speeds_of_transitions with correct rounding
        speeds_of_transitions = []
        for current, next_ in dynamic_key_frame_influence_values[:-1]:
            if next_ is not None:
                inverted_speed = next_ / 2
                original_speed = 1.0 - inverted_speed
                speeds_of_transitions.append(round(original_speed, 2))  # Ensure proper rounding
        
        # Reconstructing distances_to_next_frames with exact values
        distances_to_next_frames = []
        for i in range(1, len(dynamic_frame_distribution_values)):
            distances_to_next_frames.append(dynamic_frame_distribution_values[i] - dynamic_frame_distribution_values[i-1])
        
        return strength_of_frames,freedoms_between_frames, speeds_of_transitions

    def identify_type_of_motion_context(context_length, context_stride, context_overlap):
        # Given the context settings, identify the type of motion context
        if context_stride == 1 and context_overlap == 2:
            return "Low"
        elif context_stride == 2 and context_overlap == 4:
            return "Standard"
        elif context_stride == 4 and context_overlap == 4:
            return "High"
        else:
            return "Unknown"  # Fallback case if the inputs do not match expected values
        
    def calculate_strength_of_adherence(multipled_base_end_percent):
        return multipled_base_end_percent / (0.05 * 10)

    def reverse_frame_prompts_formatting(formatted_prompts):
        # Extract frame number and prompt pairs using a regular expression
        prompt_pairs = re.findall(r'\"(\d+\.\d+)\":\s*\"(.*?)\"', formatted_prompts)
        
        # Initialize an empty list to collect prompts
        original_prompts = [prompt for frame, prompt in prompt_pairs]
        
        return original_prompts


    def reverse_motion_strengths_formatting(formatted_motions, buffer):
        # Extract frame number and motion strength pairs using a regular expression
        motion_pairs = re.findall(r'(\d+):\((.*?)\)', formatted_motions)
        
        # Convert extracted pairs back to the original format, adjusting frame numbers
        original_motions = []
        for frame, strength in motion_pairs:
            original_frame = int(frame) - buffer  # Subtract buffer to get original frame number
            original_strength = float(strength)  # Convert strength back to float
            # Ensure the motion is appended in the correct order based on original frame numbers
            original_motions.append(original_strength)
        
        return original_motions
    

    def safe_eval(input_data):
        if isinstance(input_data, str):
            try:
                return ast.literal_eval(input_data)
            except ValueError:
                # Handle the case where the string cannot be parsed
                return input_data
        else:
            return input_data

    dynamic_strength_values = safe_eval(dynamic_strength_values)
    dynamic_key_frame_influence_values = safe_eval(dynamic_key_frame_influence_values)
    dynamic_frame_distribution_values = safe_eval(dynamic_frame_distribution_values)

    context_length = int(context_length)
    context_stride = int(context_stride)
    context_overlap = int(context_overlap)
    multipled_base_end_percent = float(multipled_base_end_percent)    

    # Step 1: Reverse dynamic_strength_values and dynamic_key_frame_influence_values

    strength_of_frames, freedoms_between_frames, speeds_of_transitions  = reverse_transform(dynamic_strength_values, dynamic_key_frame_influence_values, dynamic_frame_distribution_values)
    
    # Step 2: Reverse dynamic_frame_distribution_values to distances_to_next_frames
    distances_to_next_frames = [round((dynamic_frame_distribution_values[i] - dynamic_frame_distribution_values[i-1]) / 16, 2) for i in range(1, len(dynamic_frame_distribution_values))]
    
    # Step 3: Identify type_of_motion_context
    type_of_motion_context = identify_type_of_motion_context(context_length, context_stride, context_overlap)
    
    # Step 4: Calculate strength_of_adherence from multipled_base_end_percent
    strength_of_adherence = calculate_strength_of_adherence(multipled_base_end_percent)
    
    # Step 5: Reverse frame prompts formatting

    individual_prompts = reverse_frame_prompts_formatting(formatted_individual_prompts) 

    individual_negative_prompts = reverse_frame_prompts_formatting(formatted_individual_negative_prompts)

    # Step 6: Reverse motion strengths formatting
    motions_during_frames = reverse_motion_strengths_formatting(formatted_motions, buffer)

    return strength_of_frames, freedoms_between_frames, speeds_of_transitions, distances_to_next_frames, type_of_motion_context, strength_of_adherence, individual_prompts, individual_negative_prompts, motions_during_frames
    
