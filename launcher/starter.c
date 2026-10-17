// "Mulle Meck.exe": starts the launcher with the Python packaged next to it
// (runtime\pythonw.exe -m launcher --root <this folder>), without a console
// window. Built by tools/build-launcher-windows.sh with MinGW; extra
// arguments are passed on (e.g. --fullscreen).
#include <windows.h>
#include <wchar.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
	wchar_t dir[MAX_PATH], python[MAX_PATH + 32], line[3 * MAX_PATH + 1024];
	DWORD n = GetModuleFileNameW(NULL, dir, MAX_PATH);
	if (n == 0 || n >= MAX_PATH)
		return 1;
	wchar_t *slash = wcsrchr(dir, L'\\');
	if (slash)
		*slash = 0;
	swprintf(python, sizeof python / sizeof *python, L"%ls\\runtime\\pythonw.exe", dir);
	swprintf(line, sizeof line / sizeof *line, L"\"%ls\" -m launcher --root \"%ls\" %ls", python, dir, args ? args : L"");

	STARTUPINFOW si = { sizeof si };
	PROCESS_INFORMATION pi;
	if (!CreateProcessW(python, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
		MessageBoxW(NULL, L"runtime\\pythonw.exe", L"Mulle Meck", MB_ICONERROR);
		return 1;
	}
	CloseHandle(pi.hThread);
	CloseHandle(pi.hProcess);
	return 0;
}
