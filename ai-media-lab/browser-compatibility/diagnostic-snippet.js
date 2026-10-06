// Review-only diagnostic snippet. Not deployed. Run only in an authorized test page.
// Does not fetch media, cookies, headers, tokens or upload any diagnostic data.
for (const v of document.querySelectorAll('video')) {
  const log = event => console.log({event, errorCode:v.error?.code ?? null,
    errorMessage:v.error?.message ?? null, networkState:v.networkState,
    readyState:v.readyState, currentTime:v.currentTime,
    videoWidth:v.videoWidth, videoHeight:v.videoHeight,
    canPlay:v.canPlayType('video/mp4; codecs="avc1.64001F, mp4a.40.2"')});
  for (const e of ['loadedmetadata','canplay','playing','waiting','stalled','error','ended'])
    v.addEventListener(e,()=>log(e));
  log('snapshot');
}
