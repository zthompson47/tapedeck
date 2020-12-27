use std::{mem, thread, time};
use libc::{
    cfmakeraw, tcgetattr, tcsetattr,
    STDIN_FILENO, TCSANOW, TCSAFLUSH,
};
use structopt::StructOpt;

#[derive(StructOpt)]
struct Cli {
    #[structopt(short, long)]
    raw: bool,
    #[structopt(short, long)]
    print: bool,
}

fn main() {
    let args = Cli::from_args();
    if args.print {
        unsafe {
            let mut termios = mem::zeroed();
            tcgetattr(STDIN_FILENO, &mut termios);
            println!("{}", termios.c_iflag); // u32
            println!("{}", termios.c_oflag); // u32
            println!("{}", termios.c_cflag); // u32
            println!("{}", termios.c_line); // u8
            println!("{:?}", termios.c_cc); // [u8]
            println!("{}", termios.c_ispeed); // u32
            println!("{}", termios.c_ospeed); // u32
        }
    }
    if args.raw {
        unsafe {
            let mut termios = mem::zeroed();
            tcgetattr(STDIN_FILENO, &mut termios);
            cfmakeraw(&mut termios);
            tcsetattr(STDIN_FILENO, TCSANOW, &termios);
            thread::sleep(time::Duration::from_millis(5000));
        }
    } else {
        unsafe {
            let mut termios: libc::termios = mem::zeroed();
            termios.c_iflag = 1280u32;
            termios.c_oflag = 5u32;
            termios.c_cflag = 191u32;
            termios.c_line = 0u8;
            termios.c_cc = [
                3, 28, 127, 21, 4, 0, 1, 0,
                17, 19, 26, 0, 18, 15, 23, 22,
                0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0
            ];
            termios.c_ispeed = 15u32;
            termios.c_ospeed = 15u32;
            //tcsetattr(STDIN_FILENO, TCSANOW, &termios);
            tcsetattr(STDIN_FILENO, TCSAFLUSH, &termios);
        }
    }
}
