    path('list_plugins/',list_plugins,name='list_plugins'),
    path('enable_plugin/',enable_plugin ,name='enable_plugin'),  
    path('config_llm/',config_llm,name='config_llm'),   
    path('is_authorized/',is_authorized,name='is_authorized'),
    path('list_llm_models/',list_llm_models ,name='list_llm_models'),
    path('create_api_details/',create_api_details,name='create_api_details'),
    path('update_api_details/',update_api_details,name='update_api_details'),
    path('update_files/',update_files,name='update_files'),
    path('config_file/',config_file,name='config_file'),
    path('create_session/',create_session,name='create_session'),
    path('create_admin_session/',create_admin_session,name='create_admin_session'),
    path('create_draft_plugin_session/',create_draft_plugin_session,name='create_draft_plugin_session'),
    path('send_message/',send_message,name='send_message') ,
    path('delete_plugin/',delete_plugin,name='delete_plugin'),
    path('update_packges/',update_packages,name='update_packges'),
    path('admin_send_message/',admin_send_message,name='admin_send_message'),
    path('draft_plugin_send_message/',draft_plugin_send_message,name='draft_plugin_send_message'),
    path('list_admin_plugins/',list_admin_plugins,name="list_admin_plugins"),
    path('list_draft_plugins/',list_draft_plugins,name="list_draft_plugins"),
    path('approve_plugin/',approve_plugin,name="approve_plugin")
