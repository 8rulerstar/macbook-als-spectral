import ctypes, ctypes.util, struct, time, sys, csv
iokit=ctypes.CDLL(ctypes.util.find_library("IOKit")); cf=ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
V=ctypes.c_void_p
for f,r,a in [("IOServiceMatching",V,[ctypes.c_char_p]),("IOServiceGetMatchingServices",ctypes.c_int,[ctypes.c_uint,V,ctypes.POINTER(ctypes.c_uint)]),
 ("IOIteratorNext",ctypes.c_uint,[ctypes.c_uint]),("IOHIDDeviceCreate",V,[V,ctypes.c_uint]),("IOHIDDeviceOpen",ctypes.c_int,[V,ctypes.c_uint]),
 ("IOHIDDeviceScheduleWithRunLoop",None,[V,V,V]),("IOHIDDeviceRegisterInputReportCallback",None,[V,V,ctypes.c_long,V,V]),
 ("IORegistryEntryCreateCFProperty",V,[ctypes.c_uint,V,V,ctypes.c_uint])]:
  fn=getattr(iokit,f);fn.restype=r;fn.argtypes=a
cf.CFStringCreateWithCString.restype=V;cf.CFStringCreateWithCString.argtypes=[V,ctypes.c_char_p,ctypes.c_uint]
cf.CFStringGetCString.argtypes=[V,ctypes.c_char_p,ctypes.c_long,ctypes.c_uint]
cf.CFRunLoopGetCurrent.restype=V;cf.CFRunLoopRunInMode.argtypes=[V,ctypes.c_double,ctypes.c_bool]
S=lambda s:cf.CFStringCreateWithCString(None,s.encode(),0x08000100)
mode=V.in_dll(cf,"kCFRunLoopDefaultMode")
PH=[("기준(그대로)",5),("센서 가리기(카메라 옆을 손가락으로)",5),("빨강 화면 대기",6),("초록 화면 대기",6),("파랑 화면 대기",6),("흰 화면 대기",6),("손전등(폰 플래시)",6),("기준(그대로)",5)]
out=sys.argv[1]; rows=[]; t0=[None]; cur=[""]
CB=ctypes.CFUNCTYPE(None,V,ctypes.c_int,V,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint8),ctypes.c_long)
def cb(ctx,res,snd,typ,rid,rep,ln,*a):
  b=bytes(rep[:ln]); ch=struct.unpack_from("<5I",b,20); lux=struct.unpack_from("<f",b,40)[0]
  rows.append([round(time.time()-t0[0],2),cur[0],*ch,round(lux,1),b.hex()])
c=CB(cb); buf=(ctypes.c_uint8*256)()
it=ctypes.c_uint(); iokit.IOServiceGetMatchingServices(0,iokit.IOServiceMatching(b"AppleSPUHIDDevice"),ctypes.byref(it))
while (s:=iokit.IOIteratorNext(it)):
  p=iokit.IORegistryEntryCreateCFProperty(s,S("Product"),None,0); bb=ctypes.create_string_buffer(64)
  if p: cf.CFStringGetCString(p,bb,64,0x08000100)
  if bb.value==b"als":
    d=iokit.IOHIDDeviceCreate(None,s); assert iokit.IOHIDDeviceOpen(d,0)==0
    iokit.IOHIDDeviceRegisterInputReportCallback(d,buf,256,ctypes.cast(c,V),None)
    iokit.IOHIDDeviceScheduleWithRunLoop(d,cf.CFRunLoopGetCurrent(),mode); break
t0[0]=time.time()
for name,sec in PH:
  cur[0]=name; print(f"\n>>> {name} ({sec}초)",flush=True); end=time.time()+sec; last=0
  while time.time()<end:
    cf.CFRunLoopRunInMode(mode,0.1,False)
    if rows and time.time()-last>1: last=time.time(); r=rows[-1]; print("   ch",r[2:7],"lux",r[7],flush=True)
with open(out,"w",newline="") as f: w=csv.writer(f); w.writerow(["t","phase","c0","c1","c2","c3","c4","lux","hex"]); w.writerows(rows)
print("\n끝. 저장:",out)
