/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} full_name
 * @property {string} email
 * @property {string} plan
 * @property {Object} preferences
 * @property {string} created_at
 */

/**
 * @typedef {Object} Character
 * @property {string} [id]
 * @property {string} name
 * @property {string} description
 * @property {"protagonist"|"antagonist"|"supporting"} role
 * @property {string} [voice_profile]
 * @property {string} [reference_image_path]
 */

/**
 * @typedef {Object} Scene
 * @property {string} id
 * @property {number} index
 * @property {string} text
 * @property {string} location
 * @property {string} emotion
 * @property {string} camera_movement
 * @property {number} duration_seconds
 * @property {string[]} sfx_tags
 * @property {string} music_mood
 * @property {string} status
 * @property {string} [image_path]
 * @property {string} [clip_path]
 */

/**
 * @typedef {Object} Project
 * @property {string} id
 * @property {string} title
 * @property {string} prompt
 * @property {string} story
 * @property {string} dialogue
 * @property {string} animation_style
 * @property {number} duration_minutes
 * @property {string} resolution
 * @property {string} status
 * @property {string} current_stage
 * @property {number} progress_percent
 * @property {string} error_message
 * @property {string} thumbnail_path
 * @property {string} video_path
 * @property {string} subtitle_path
 * @property {string} created_at
 * @property {string} updated_at
 * @property {Character[]} [characters]
 * @property {Scene[]} [scenes]
 */

export {};
