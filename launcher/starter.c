// "Mulle Meck.exe": starts the launcher with the Python packaged next to it
// (runtime\pythonw.exe -m launcher --root <this folder>), without a console
// window. Built by tools/build-launcher-windows.sh with MinGW; extra
// arguments are passed on (e.g. --fullscreen). Built with -DPLAY_ID=L"..."
// it is a game's own starter ("Bygg bilar.exe"): --play that game.
#include <windows.h>
#include <wchar.h>

#ifdef PLAY_ID
#define PLAY L"--play " PLAY_ID L" "
#else
#define PLAY L""
#endif

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR args, int show) {
	wchar_t dir[MAX_PATH], python[MAX_PATH + 32], line[3 * MAX_PATH + 1024];
	DWORD n = GetModuleFileNameW(NULL, dir, MAX_PATH);
	if (n == 0 || n >= MAX_PATH)
		return 1;
	wchar_t *slash = wcsrchr(dir, L'\\');
	if (slash)
		*slash = 0;
	swprintf(python, sizeof python / sizeof *python, L"%ls\\runtime\\pythonw.exe", dir);
	swprintf(line, sizeof line / sizeof *line, L"\"%ls\" -m launcher --root \"%ls\" %ls%ls", python, dir, PLAY, args ? args : L"");

	STARTUPINFOW si = { sizeof si };
	PROCESS_INFORMATION pi;
	if (!CreateProcessW(python, line, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi)) {
		// Usually a starter dragged out of the folder (which moves it).
		MessageBoxW(NULL, L"Hittar inte resten av Mulle Meck.\n\n"
			L"Den h\x00e4r filen m\x00e5ste ligga kvar i mappen MulleMeck. Vill du ha den p\x00e5 "
			L"Skrivbordet: flytta tillbaka den, h\x00f6gerklicka p\x00e5 den och v\x00e4lj "
			L"Skicka till > Skrivbord (skapa genv\x00e4g).",
			L"Mulle Meck", MB_ICONERROR);
		return 1;
	}
	CloseHandle(pi.hThread);
	CloseHandle(pi.hProcess);
	return 0;
}
