# Colima settings
## M Series Mac 
```bash
colima start --cpu-type host --arch host --vm-type=vz --mount-type virtiofs -c 8 -m 16
```

## Intel Mac
```bash
colima start --cpu-type host --arch host --vm-type=vz --vz-rosetta --mount-type virtiofs -c 8 -m 16
```