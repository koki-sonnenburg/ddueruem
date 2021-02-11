BUDDY_SRC 		= .cache/buddy-2.4/src

CC 			= gcc
CFLAGS 		= -DSPECIALIZE_RELPROD -DSPECIALIZE_AND -DSPECIALIZE_OR -DSMALL_NODES -O2 -fomit-frame-pointer -fPIC $(EXTRA_CFLAGS)

INCLUDES 	= 	-I. -I/usr/include \
        		-I$(BUDDY_SRC) -I$(BUDDY_SRC)/..

BUDDY_DLL_NAME 	= libbuddy.so
BUDDY_SRCS = $(BUDDY_SRC)/bddio.c $(BUDDY_SRC)/bddop.c $(BUDDY_SRC)/bvec.c \
	$(BUDDY_SRC)/cache.c $(BUDDY_SRC)/fdd.c $(BUDDY_SRC)/imatrix.c \
	$(BUDDY_SRC)/kernel.c $(BUDDY_SRC)/pairs.c $(BUDDY_SRC)/prime.c \
	$(BUDDY_SRC)/reorder.c $(BUDDY_SRC)/tree.c

BUDDY_OBJS = $(BUDDY_SRCS:.c=.o)

default: buddy

buddy: $(BUDDY_DLL_NAME)

$(BUDDY_DLL_NAME): $(BUDDY_OBJS)
	$(CC) -o $@ $(BUDDY_OBJS) -shared

%.o: %.c 
	$(CC) -c -o $@ $< $(CFLAGS) $(INCLUDES) 

clean:
	$(RM) -f $(BUDDY_OBJS) $(BUDDY_DLL_NAME)
