# 🔍 Troubleshooting Guide

## Issue: Application Not Processing

### Quick Diagnostic Steps

#### Step 1: Verify Server is Running
```bash
python debug_api.py
```

**Expected Output:**
```
[OK] Home page loads
Found 4 transformations
```

**If this fails:** Server isn't running. Start it with `python start_fastapi.py`

---

#### Step 2: Open Browser DevTools

1. Open **http://localhost:8000** in browser
2. Press **F12** to open Developer Tools
3. Go to **Console** tab
4. Look for any red error messages

---

#### Step 3: Test Upload Flow

1. **Upload a Document:**
   - Click "Browse files"
   - Select a `.docx` file
   - **Check Console** - Should see:
     ```
     Uploading file: filename.docx
     Upload response: {success: true, ...}
     Document uploaded successfully
     ```

2. **If you see errors:**
   - ❌ "Upload failed: 400" → File format issue (use .docx not .doc)
   - ❌ "Upload failed: 500" → Server error (check terminal for Python errors)
   - ❌ Network error → Server not responding

---

#### Step 4: Test Transformation Flow

1. **Select Transformation Type:**
   - Choose from dropdown (e.g., "Technical Guide to FAQs")
   
2. **Click "Draft" Button**

3. **Check Console** - Should see:
   ```
   Starting Draft... tech_to_faq
   EventSource connection opened
   SSE Message: {"type":"step_status","step":0,...}
   SSE Message: {"type":"stream","step":0,...}
   Transformation complete!
   ```

4. **If nothing happens:**
   - Check if button is disabled (gray)
   - Ensure document is uploaded
   - Ensure transformation is selected

---

### Common Issues & Fixes

#### Issue 1: "Draft" Button is Grayed Out
**Cause:** Missing document or transformation selection

**Fix:**
- [ ] Upload a document first
- [ ] Select transformation type from dropdown

---

#### Issue 2: No Console Logs Appear
**Cause:** JavaScript not loading or Alpine.js issue

**Fix:**
1. Hard refresh: **Ctrl+Shift+R** (or Cmd+Shift+R on Mac)
2. Clear browser cache
3. Try different browser (Chrome/Firefox)

---

#### Issue 3: EventSource Connection Fails
**Symptoms in Console:**
```
EventSource error: ...
Connection error. Please check console for details.
```

**Fix:**
1. Check server terminal for errors
2. Verify API key is set in `app_fastapi.py` line 27
3. Check internet connection (needs to reach OpenAI)

---

#### Issue 4: Streaming Starts but No Text Appears
**Symptoms:**
- Actions panel shows steps
- Outputs panel stays empty

**Possible Causes:**
1. **OpenAI API Error** - Check terminal for errors
2. **API Key Invalid** - Verify key is correct
3. **Rate Limit** - Wait a minute and try again

**Debug:**
```bash
python test_streaming.py
```

This will show if OpenAI is responding correctly.

---

### Browser Console Commands

Open Console (F12) and try these:

#### Check if Alpine.js is loaded:
```javascript
console.log(window.Alpine)
```
Should show Alpine object, not `undefined`

#### Check current state:
```javascript
// This won't work directly, but you can see state in Vue DevTools
```

#### Manually test API:
```javascript
fetch('/api/transformations')
  .then(r => r.json())
  .then(d => console.log(d))
```
Should show list of transformations

---

### Network Tab Debugging

1. Open DevTools → **Network** tab
2. Click "Draft" button
3. Look for:
   - `upload` request (should be 200 OK)
   - `stream/tech_to_faq` request (should be 200 OK, type: eventsource)

4. Click on `stream/...` request
5. Go to **Response** or **Messages** tab
6. Should see streaming messages like:
   ```
   data: {"type":"step_status",...}
   data: {"type":"stream",...}
   ```

---

### Server-Side Debugging

#### Check Terminal Output
When you click "Draft", terminal should show:
```
INFO:     127.0.0.1:xxxxx - "GET /api/stream/tech_to_faq HTTP/1.1" 200 OK
```

If you see errors, they'll appear here.

#### Test Backend Directly:
```bash
python test_streaming.py
```

This tests the full workflow without the browser.

---

### Step-by-Step Verification

Run these in order:

#### ✅ Step 1: Server Health
```bash
python debug_api.py
```
**Must pass** before continuing.

#### ✅ Step 2: Components
```bash
python test_app.py
```
Should show `[SUCCESS] All components ready!`

#### ✅ Step 3: Streaming
```bash
python test_streaming.py
```
Should show steps completing.

#### ✅ Step 4: Browser Test
1. Open http://localhost:8000
2. Open DevTools Console (F12)
3. Upload document → Check for "Document uploaded successfully"
4. Select transformation
5. Click Draft → Check for "Starting Draft..."
6. Watch for SSE messages in console

---

### What Each Log Means

**Good Logs (Everything Working):**
```
Uploading file: test.docx          ← File selected
Upload response: {success: true}    ← Server received it
Document uploaded successfully       ← File processed
Starting Draft... tech_to_faq       ← Transformation starting
EventSource connection opened        ← SSE connected
SSE Message: {"type":"step_status"} ← Steps being set up
SSE Message: {"type":"stream"}      ← AI output streaming
Transformation complete!             ← Done!
```

**Bad Logs (Something Wrong):**
```
Upload error: ...                   ← File upload failed
EventSource error: ...              ← Connection failed
Error: No document uploaded         ← Upload didn't work
```

---

### Quick Fixes

#### Nothing Works:
1. Restart server: `Ctrl+C`, then `python start_fastapi.py`
2. Hard refresh browser: `Ctrl+Shift+R`
3. Check API key in `app_fastapi.py`

#### Upload Works, Draft Doesn't:
1. Check browser console for errors
2. Verify transformation is selected
3. Check Network tab for streaming request

#### Draft Starts, No Output:
1. Check server terminal for errors
2. Test with `python test_streaming.py`
3. Verify OpenAI API key and quota

---

### Getting Help

If still stuck, gather this info:

1. **Browser Console logs** (copy all text)
2. **Server terminal output** (copy last 20 lines)
3. **Network tab screenshot** (showing the stream request)
4. **What you did** (step by step)

Then check:
- OpenAI API key is valid
- Internet connection is working
- No firewall blocking localhost:8000
- Using .docx files (not .doc or .pdf)

---

## Success Checklist

When working correctly, you should see:

- [x] Server starts without errors
- [x] http://localhost:8000 loads
- [x] Browser console shows no errors
- [x] File upload shows "✅ filename (X words)"
- [x] Draft button is blue (not gray)
- [x] Click Draft → Actions panel shows steps
- [x] Outputs panel shows streaming text
- [x] Text updates word-by-word
- [x] Export creates .docx file

If ALL are checked, it's working! 🎉

