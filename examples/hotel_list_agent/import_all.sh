orchestrate connections add  --app-id wxai 

orchestrate connections configure \
    --app-id wxai \
    --env draft \
    --type team \
    --kind key_value 

orchestrate connections set-credentials \
    --app-id wxai \
    --env draft \
    -e space_id=$WXAI_SPACE_ID \
    -e apikey=$WXAI_API_KEY \

orchestrate agents create --style custom --package-root .

orchestrate agents connect -n hotel_list_agent -a wxai